"""UL App Bridge runtime — verbs → policy → provenance → K32-class intents."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from ul_app_bridge.classifier import classify_binary
from ul_app_bridge.pid_sigil_registry import PidSigilRegistry, SigilRecord
from ul_app_bridge.policy import check_cap, check_path, load_policy, profile_for_sigil_record
from ul_app_bridge.provenance import ULBridgeProvenance
from ul_app_bridge.schema import UL_BRIDGE_VERSION, normalize_verb, ul_response
from ul_app_bridge.seccomp_v0 import export_spec, profile_spec, try_apply_to_pid


class ULAppBridge:
    def __init__(self) -> None:
        self.policy = load_policy()
        self.registry = PidSigilRegistry()
        self.provenance = ULBridgeProvenance()
        spec_path = cogos_root() / "memory" / "ul_app_bridge" / "seccomp_foreign_app_ul_bridge.json"
        export_spec(spec_path)

    def admit_foreign_exec(
        self,
        binary_path: str,
        *,
        pid: Optional[int] = None,
        profile_id: Optional[str] = None,
        spawn_mode: str = "inherit",
        parent_pid: Optional[int] = None,
    ) -> Dict[str, Any]:
        pid = pid if pid is not None else os.getpid()
        info = classify_binary(binary_path)
        if not info.get("foreign") and info.get("backend") == "linux-native":
            return {"ok": True, "governed": False, "reason": "linux_native_optional_shim"}

        profile_id = str(profile_id or info.get("profile_id", "profile.linux.foreign"))
        prof = (self.policy.get("profiles") or {}).get(profile_id, {})
        parent = self.registry.lookup(parent_pid) if parent_pid else None
        caps = list(prof.get("caps") or [])
        if spawn_mode == "delegated" and parent:
            requested = list(prof.get("caps") or [])
            caps = [c for c in requested if c in parent.caps]
            sigil = PidSigilRegistry.derive_child_sigil(parent, caps)
            record = self.registry.register(
                pid,
                profile_id=profile_id,
                bridge_class=str(prof.get("bridge_class", "foreign_app_ul_bridge")),
                backend=str(info.get("backend", "unknown")),
                caps=caps,
                sigil=sigil,
                parent_sigil=parent.sigil,
                spawn_mode="delegated",
                binary_hint=Path(binary_path).name,
            )
        elif parent and spawn_mode == "inherit":
            record = self.registry.register(
                pid,
                profile_id=parent.profile_id,
                bridge_class=parent.bridge_class,
                backend=parent.backend,
                caps=parent.caps,
                sigil=parent.sigil,
                parent_sigil=parent.sigil,
                spawn_mode="inherit",
                binary_hint=Path(binary_path).name,
            )
        else:
            record = self.registry.register(
                pid,
                profile_id=profile_id,
                bridge_class=str(prof.get("bridge_class", "foreign_app_ul_bridge")),
                backend=str(info.get("backend", "unknown")),
                caps=caps,
                binary_hint=Path(binary_path).name,
            )

        seccomp = try_apply_to_pid(pid)
        self.provenance.append(
            {
                "kind": "exec.admit",
                "sigil": record.sigil,
                "binary": binary_path,
                "profile_id": record.profile_id,
                "backend": record.backend,
                "seccomp": seccomp,
            }
        )
        return {
            "ok": True,
            "governed": True,
            "pid": pid,
            "sigil": record.sigil,
            "profile_id": record.profile_id,
            "backend": record.backend,
            "seccomp": seccomp,
        }

    def dispatch(
        self,
        verb: str,
        args: Dict[str, Any],
        *,
        caller_pid: Optional[int] = None,
    ) -> Dict[str, Any]:
        caller_pid = caller_pid if caller_pid is not None else os.getpid()
        record = self.registry.lookup(caller_pid)
        if not record:
            return ul_response(
                ok=False,
                error="ERR_SIGIL_FORBIDDEN",
                policy="unregistered_pid",
                details=f"PID {caller_pid} has no OS-assigned sigil",
            )

        args = dict(args or {})
        args.pop("sigil", None)
        trace_id = args.pop("trace_id", None) or str(uuid.uuid4())[:12]
        norm = normalize_verb(verb)
        prof = profile_for_sigil_record(record.to_dict(), self.policy)

        handlers = {
            "handshake": self._handshake,
            "fs.read": self._fs_read,
            "fs.write": self._fs_write,
            "fs.list": self._fs_list,
            "net.request": self._net_request,
            "proc.spawn": self._proc_spawn,
            "log.write": self._log_write,
            "tool.invoke": self._tool_invoke,
        }
        handler = handlers.get(norm)
        if not handler:
            return ul_response(ok=False, error="ERR_TOOL_NOT_FOUND", details=f"unknown verb {verb}")

        result = handler(record, prof, args, trace_id=trace_id)
        self.provenance.append(
            {
                "kind": "verb",
                "verb": norm,
                "sigil": record.sigil,
                "trace_id": trace_id,
                "ok": result.get("ok"),
                "error": result.get("error"),
                "policy": result.get("policy"),
                "path": args.get("path"),
            }
        )
        return result

    def _handshake(
        self,
        record: SigilRecord,
        prof: Dict[str, Any],
        args: Dict[str, Any],
        *,
        trace_id: str,
    ) -> Dict[str, Any]:
        client = str(args.get("client", "unknown"))
        ul_version = str(args.get("ul_version", UL_BRIDGE_VERSION))
        if ul_version.split(".")[0] != UL_BRIDGE_VERSION.split(".")[0]:
            return ul_response(
                ok=False,
                error="ERR_UL_VERSION_UNSUPPORTED",
                details=f"client wants {ul_version}",
            )
        caps = {fam: any(c.startswith(fam) for c in record.caps) for fam in ("fs", "net", "proc", "tool")}
        return ul_response(
            ok=True,
            data={
                "negotiated_ul_version": UL_BRIDGE_VERSION,
                "sigil": record.sigil,
                "capabilities": caps,
                "client": client,
                "trace_id": trace_id,
            },
        )

    def _fs_read(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("fs.read", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_fs_read")
        path = str(args.get("path", ""))
        ok, err, pol = check_path(path, prof, write=False)
        if not ok:
            return ul_response(ok=False, error=err, policy=pol, details=path)
        p = Path(path.replace("\\", "/"))
        if not p.is_file():
            return ul_response(ok=False, error="ERR_FS_NOT_FOUND", details=path)
        try:
            data = p.read_bytes()
        except OSError as exc:
            return ul_response(ok=False, error="ERR_FS_IO", details=str(exc))
        return ul_response(ok=True, data={"data": data.decode("utf-8", errors="replace"), "trace_id": trace_id})

    def _fs_write(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("fs.write", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_fs_write")
        path = str(args.get("path", ""))
        ok, err, pol = check_path(path, prof, write=True)
        if not ok:
            return ul_response(ok=False, error=err, policy=pol, details=path)
        p = Path(path.replace("\\", "/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        data = args.get("data", "")
        if isinstance(data, bytes):
            payload = data
        else:
            payload = str(data).encode("utf-8")
        mode = str(args.get("mode", "create_or_overwrite"))
        try:
            if mode == "append" and p.exists():
                with p.open("ab") as fh:
                    fh.write(payload)
            else:
                p.write_bytes(payload)
        except OSError as exc:
            return ul_response(ok=False, error="ERR_FS_IO", details=str(exc))
        return ul_response(ok=True, data={"bytes_written": len(payload), "trace_id": trace_id})

    def _fs_list(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("fs.list", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_fs_list")
        path = str(args.get("path", "."))
        ok, err, pol = check_path(path, prof, write=False)
        if not ok:
            return ul_response(ok=False, error=err, policy=pol, details=path)
        p = Path(path.replace("\\", "/"))
        if not p.is_dir():
            return ul_response(ok=False, error="ERR_FS_NOT_FOUND", details=path)
        entries = []
        for child in sorted(p.iterdir())[:200]:
            entries.append({"name": child.name, "kind": "dir" if child.is_dir() else "file"})
        return ul_response(ok=True, data={"entries": entries, "trace_id": trace_id})

    def _net_request(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("net.request", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_net_request")
        if not prof.get("net_allowed"):
            return ul_response(ok=False, error="ERR_NET_FORBIDDEN", policy="net_disabled_for_profile")
        url = str(args.get("url", ""))
        if "evil.example" in url:
            return ul_response(ok=False, error="ERR_NET_FORBIDDEN", policy="deny_blocklist_host", details=url)
        return ul_response(
            ok=True,
            data={
                "status": 200,
                "headers": {"content-type": "application/json"},
                "body": json.dumps({"stub": True, "url": url, "method": args.get("method", "GET")}),
                "trace_id": trace_id,
            },
        )

    def _proc_spawn(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("proc.spawn", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_proc_spawn")
        spawn_mode = str(args.get("spawn_mode", "inherit"))
        command = str(args.get("command", ""))
        child_pid = os.getpid() + 10000
        admit = self.admit_foreign_exec(command, pid=child_pid, spawn_mode=spawn_mode, parent_pid=record.pid)
        if not admit.get("ok"):
            return ul_response(ok=False, error="ERR_PROC_FORBIDDEN", details=str(admit))
        return ul_response(ok=True, data={"pid": child_pid, "sigil": admit.get("sigil"), "trace_id": trace_id})

    def _log_write(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("log.write", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_log_write")
        channel = str(args.get("channel", f"app.{record.sigil}"))
        log_path = cogos_root() / "memory" / "ul_app_bridge" / "channels" / f"{channel}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "level": args.get("level", "info"),
            "message": args.get("message", ""),
            "sigil": record.sigil,
            "trace_id": trace_id,
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return ul_response(ok=True, data={"trace_id": trace_id})

    def _tool_invoke(self, record: SigilRecord, prof: Dict[str, Any], args: Dict[str, Any], *, trace_id: str) -> Dict[str, Any]:
        ok_cap, _ = check_cap("tool.invoke", record.caps)
        if not ok_cap:
            return ul_response(ok=False, error="ERR_TOOL_FORBIDDEN", policy="cap_tool_invoke")
        return ul_response(
            ok=True,
            data={"result": {"name": args.get("name"), "stub": True}, "trace_id": trace_id},
        )

    def governance_summary(self, sigil: Optional[str] = None) -> Dict[str, Any]:
        lines = []
        path = self.provenance.path
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines()[-50:]:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if sigil and row.get("sigil") != sigil:
                    continue
                lines.append(row)
        return {"events": lines[-20:], "verify": self.provenance.verify(), "seccomp": profile_spec()}
