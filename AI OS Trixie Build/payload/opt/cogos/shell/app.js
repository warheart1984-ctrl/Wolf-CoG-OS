const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "files", label: "Files" },
  { id: "settings", label: "Settings" },
  { id: "creative", label: "Creative" },
  { id: "devices", label: "Devices" },
  { id: "drivers", label: "Drivers" },
  { id: "mesh", label: "Family Mesh" },
  { id: "ecosystem", label: "Ecosystem" },
];

let state = { tab: "dashboard", cc: null, filesPath: "", settings: null, drivers: null };

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

async function action(name, params = {}, profile_id = "operator") {
  return api("/api/operator/json", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: name, params, profile_id }),
  });
}

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function setStatus(ok, text) {
  const el = document.getElementById("status-pill");
  el.textContent = text;
  el.className = "status" + (ok ? " ok" : "");
}

async function refresh() {
  try {
    state.cc = await api("/api/control-center");
    state.settings = state.cc.settings || (await api("/api/settings"));
    setStatus(true, `v${state.cc.phase3?.release?.version || "?"} · eval ${state.cc.phase3?.eval?.passed}/${state.cc.phase3?.eval?.total}`);
    render();
  } catch (e) {
    setStatus(false, "offline");
    document.getElementById("view").innerHTML = `<div class="card"><p>Start desktop: <code>cogos-desktop-start</code></p><pre>${esc(e)}</pre></div>`;
  }
}

function renderTabs() {
  const nav = document.getElementById("tabs");
  nav.innerHTML = TABS.map(
    (t) => `<button class="${state.tab === t.id ? "active" : ""}" data-tab="${t.id}">${t.label}</button>`
  ).join("");
  nav.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => { state.tab = btn.dataset.tab; render(); };
  });
}

function renderDashboard() {
  const p1 = state.cc;
  const p3 = state.cc.phase3 || {};
  const op = p1.operator_dashboard || {};
  const lp = p1.law_pulse || {};
  return `
    <div class="grid2">
      <div class="card"><h2>Operator</h2>
        <div class="metric">${esc(op.active_profile)}</div>
        <div class="sub">PID1 ${op.pid1_ok ? "OK" : "FAIL"} · daemon ${op.daemon_running ? "RUN" : "STOP"}</div>
        <div class="row" style="margin-top:0.75rem">
          <button class="secondary" onclick="doAction('hal_refresh')">Refresh HAL</button>
          <button class="secondary" onclick="doAction('eval_run')">Run eval</button>
        </div>
      </div>
      <div class="card"><h2>LawPulse</h2>
        <div class="metric">${esc(lp.law_version)}</div>
        <div class="sub">Ledger ${lp.ledger_health?.ok ? "OK" : "FAIL"} · drift ${lp.drift_composite}</div>
        <div class="sub">Drivers pending ${lp.driver_policy?.pending_manual ?? "?"}</div>
      </div>
    </div>
    <div class="card"><h2>Release</h2>
      <span class="pill">${esc(p3.release?.version)}</span>
      <span class="pill">tier ${esc(p3.tiers?.active_tier)}</span>
      <span class="pill">packages ${p3.packages?.installed_count}/${p3.packages?.catalog_count}</span>
    </div>`;
}

async function loadFiles(path) {
  state.filesPath = path || state.filesPath || "";
  const data = await api("/api/files?path=" + encodeURIComponent(state.filesPath));
  state.files = data;
  render();
}

function renderFiles() {
  const f = state.files;
  if (!f) {
    loadFiles("");
    return "<div class='card'>Loading files…</div>";
  }
  if (!f.ok) return `<div class="card"><p>${esc(f.error)}</p></div>`;
  const rows = (f.entries || []).map((e) => {
    const cls = e.kind === "dir" ? "entry-dir" : "entry-file";
    const click = e.kind === "dir" ? `onclick="loadFiles('${esc(e.path).replace(/'/g, "\\'")}')"` : "";
    return `<tr><td class="${cls}" ${click}>${esc(e.name)}</td><td>${e.kind}</td><td>${e.size_bytes || ""}</td></tr>`;
  }).join("");
  const parent = f.parent ? `<button class="secondary" onclick="loadFiles('${esc(f.parent).replace(/'/g, "\\'")}')">↑ Parent</button>` : "";
  return `
    <div class="card">
      <h2>File manager</h2>
      <div class="path-bar">${esc(f.path)} ${parent}</div>
      <table><thead><tr><th>Name</th><th>Kind</th><th>Size</th></tr></thead><tbody>${rows || "<tr><td colspan=3 class=sub>empty</td></tr>"}</tbody></table>
    </div>`;
}

function renderSettings() {
  const s = state.settings || {};
  const fr = s.first_run || {};
  const mesh = s.mesh || {};
  const watch = s.automatic_watch || {};
  return `
    <div class="grid2">
      <div class="card"><h2>Profile & mode</h2>
        <label>Active profile</label>
        <select id="set-profile">${(s.profiles || []).map((p) =>
          `<option value="${esc(p.id)}" ${p.id === s.active_profile ? "selected" : ""}>${esc(p.display_name || p.id)}</option>`
        ).join("")}</select>
        <button onclick="saveProfile()">Switch profile</button>
        <div class="sub" style="margin-top:0.5rem">First-run: ${fr.complete ? "complete" : "pending"}</div>
      </div>
      <div class="card"><h2>Mesh trust</h2>
        <label>Mesh name</label>
        <input id="set-mesh-name" value="${esc(mesh.mesh_name || "")}">
        <label>Trusted peer sigils (comma-separated)</label>
        <textarea id="set-mesh-sigils" rows="3">${esc((mesh.trusted_peer_sigils || []).join(", "))}</textarea>
        <button onclick="saveMesh()">Save mesh</button>
      </div>
    </div>
    <div class="card"><h2>Automatic watches</h2>
      <label>Watch folders (one per line)</label>
      <textarea id="set-watch" rows="4">${esc((watch.watch_folders || []).join("\n"))}</textarea>
      <label>Daily suggestion cap</label>
      <input id="set-daily" type="number" min="1" max="10" value="${watch.max_daily_suggestions || 3}">
      <button onclick="saveWatch()">Save watches</button>
    </div>
    <div class="card"><h2>Updates</h2>
      <div class="sub">Release ${esc(s.release?.version)} — use Ship Cockpit or <code>cogos-manifest verify-core</code> on ISO.</div>
      <button class="secondary" onclick="doAction('corridor_verify')">Verify corridor</button>
    </div>`;
}

function renderCreative() {
  const c = state.cc.phase2?.creative || {};
  return `
    <div class="card"><h2>Creative lanes</h2>
      <div class="sub">Artifacts: ${c.artifacts_total || 0} · lanes: ${(c.lanes || []).join(", ")}</div>
      <div class="row">
        <button onclick="runCreative('story_forge','draft')">Story draft</button>
        <button onclick="runCreative('beatbox','score')">Beatbox score</button>
        <button onclick="runCreative('world3d','build')">World build</button>
      </div>
      <pre class="log" id="creative-log">—</pre>
    </div>`;
}

function renderDevices() {
  const ds = state.cc.device_storage || {};
  const raid = state.cc.raid || {};
  const rows = (ds.devices || []).slice(0, 16).map((d) =>
    `<tr><td>${esc(d.name)}</td><td>${esc(d.class)}</td><td>${Math.round((d.size_bytes || 0) / 1e9)} GB</td><td>${esc((d.mount || {}).target || "—")}</td></tr>`
  ).join("");
  return `
    <div class="card"><h2>Storage</h2>
      <div class="row">
        <button class="secondary" onclick="doAction('device_refresh')">Refresh</button>
        <button class="secondary" onclick="doAction('raid_scan')">RAID scan</button>
      </div>
      <div class="sub">RAID proposed ${raid.proposed || 0} · approved ${raid.approved || 0} · apply blocked</div>
      <table><thead><tr><th>Device</th><th>Class</th><th>Size</th><th>Mount</th></tr></thead><tbody>${rows}</tbody></table>
    </div>`;
}

function renderMesh() {
  const id = state.cc?.phase2?.mesh?.identity || state.settings?.mesh || {};
  const phys = state.meshPhysical || {};
  return `
    <div class="card"><h2>Family mesh (physical)</h2>
      <div class="sub">Device ${esc(id.device_id || "?")} · sigil ${esc((id.device_sigil || "").slice(0, 16))}…</div>
      <ol class="sub" style="margin:0.5rem 0 1rem 1.2rem">
        <li>Each box: <code>cogos-mesh export-identity</code> → copy <code>mesh_drop/identity/</code> via USB</li>
        <li>Each peer: <code>cogos-mesh import-peers</code></li>
        <li>Sender: <code>cogos-mesh propose</code> then <code>cogos-mesh export-drop</code></li>
        <li>Receiver: copy <code>inbox/*.json</code> → <code>cogos-mesh import-drop</code></li>
      </ol>
      <div class="row">
        <button onclick="meshAction('mesh_export_identity')">Export identity</button>
        <button onclick="meshAction('mesh_import_peers')">Import peers</button>
        <button onclick="meshAction('mesh_export_drop')">Export outbox</button>
        <button onclick="meshAction('mesh_import_drop')">Import inbox</button>
        <button onclick="meshAction('mesh_physical')">Physical proof (local)</button>
      </div>
      <pre class="log" id="mesh-log">${esc(JSON.stringify(phys, null, 2))}</pre>
    </div>`;
}

async function meshAction(name) {
  const r = await action(name);
  state.meshPhysical = r.result || r;
  document.getElementById("mesh-log").textContent = JSON.stringify(state.meshPhysical, null, 2);
}

function renderEcosystem() {
  const eco = state.cc.ecosystem || {};
  const ul = eco.ul_packages || [];
  const billing = eco.billing || {};
  const kernel = eco.kernel_eval || {};
  const k32 = eco.k32 || {};
  const soak = eco.mesh_soak_report || {};
  const rows = ul.map((p) =>
    `<tr><td>${esc(p.id)}</td><td>${esc(p.publisher)}</td><td>${p.installed ? "yes" : "no"}</td>
     <td>${p.installed ? "" : `<button class="secondary" onclick="ulInstall('${esc(p.id)}')">Install</button>`}</td></tr>`
  ).join("");
  return `
    <div class="grid2">
      <div class="card"><h2>UL packages</h2>
        <button class="secondary" onclick="doAction('ul_pkg_verify')">Verify catalog</button>
        <table><thead><tr><th>ID</th><th>Publisher</th><th>Installed</th><th></th></tr></thead><tbody>${rows}</tbody></table>
      </div>
      <div class="card"><h2>Mesh soak</h2>
        <div class="sub">Last: ${soak.ok ? "PASS" : soak.timestamp ? "see report" : "not run"} · peers ${soak.peers || 0}</div>
        <button onclick="doAction('mesh_soak')">Run family soak</button>
      </div>
    </div>
    <div class="grid2">
      <div class="card"><h2>Billing hooks</h2>
        <div class="metric">${billing.weighted_units || 0}</div>
        <div class="sub">weighted units · ${billing.allowed_events || 0} allowed events</div>
        <button class="secondary" onclick="doAction('billing_export')">Export usage</button>
      </div>
      <div class="card"><h2>Kernel eval</h2>
        <div class="sub">Status: ${esc(kernel.status)} · ready: ${kernel.ready_for_kernel_eval ? "yes" : "no"}</div>
        <ul>${(kernel.checklist || []).map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
      </div>
      <div class="card"><h2>K32 plane</h2>
        <div class="sub">LawPulse events: ${(k32.lawpulse || {}).k32_events || 0}</div>
        <button class="secondary" onclick="doAction('k32_status')">Refresh K32</button>
      </div>
    </div>`;
}

function renderDrivers() {
  const dp = state.cc.driver_policy || {};
  const evals = (dp.evaluations || []).slice(0, 20);
  const rows = evals.map((e) => {
    const approve = e.requires_manual && !e.allowed
      ? `<button class="secondary" onclick="approveDriver('${esc(e.device_id)}','${esc(e.rule_id)}')">Approve</button>`
      : (e.allowed ? "<span class=pill>allowed</span>" : "<span class=pill>blocked</span>");
    return `<tr><td>${esc(e.device_id)}</td><td>${esc(e.rule_id)}</td><td>${esc(e.module)}</td><td>${approve}</td></tr>`;
  }).join("");
  return `
    <div class="card"><h2>Driver policy</h2>
      <div class="sub">${dp.rules_count || 0} rules · ${dp.pending_manual || 0} pending manual</div>
      <button class="secondary" onclick="doAction('driver_scan').then(refresh)">Scan devices</button>
      <table><thead><tr><th>Device</th><th>Rule</th><th>Module</th><th></th></tr></thead><tbody>${rows}</tbody></table>
    </div>`;
}

function render() {
  renderTabs();
  const view = document.getElementById("view");
  if (state.tab === "dashboard") view.innerHTML = renderDashboard();
  else if (state.tab === "files") view.innerHTML = renderFiles();
  else if (state.tab === "settings") view.innerHTML = renderSettings();
  else if (state.tab === "creative") view.innerHTML = renderCreative();
  else if (state.tab === "devices") view.innerHTML = renderDevices();
  else if (state.tab === "drivers") view.innerHTML = renderDrivers();
  else if (state.tab === "mesh") view.innerHTML = renderMesh();
  else if (state.tab === "ecosystem") view.innerHTML = renderEcosystem();
}

window.ulInstall = async (id) => {
  await action("ul_pkg_install", { package_id: [id] });
  await refresh();
};

window.loadFiles = loadFiles;
window.doAction = async (name, params = {}) => {
  await action(name, params);
  await refresh();
};
window.runCreative = async (lane, verb) => {
  const r = await action("creative_run", { lane: [lane], verb: [verb], prompt: ["CoGOS shell prompt"] });
  document.getElementById("creative-log").textContent = JSON.stringify(r.result, null, 2);
  await refresh();
};
window.approveDriver = async (device_id, rule_id) => {
  await action("driver_approve", { device_id: [device_id], rule_id: [rule_id] });
  await refresh();
};
window.saveProfile = async () => {
  const id = document.getElementById("set-profile").value;
  await api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active_profile: id }) });
  await refresh();
};
window.saveMesh = async () => {
  const name = document.getElementById("set-mesh-name").value;
  const sigils = document.getElementById("set-mesh-sigils").value.split(",").map((s) => s.trim()).filter(Boolean);
  await api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mesh: { mesh_name: name, trusted_peer_sigils: sigils } }) });
  await refresh();
};
window.meshAction = meshAction;
window.saveWatch = async () => {
  const folders = document.getElementById("set-watch").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const cap = parseInt(document.getElementById("set-daily").value, 10) || 3;
  await api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ automatic_watch: { watch_folders: folders, max_daily_suggestions: cap } }) });
  await refresh();
};

refresh();
setInterval(refresh, 12000);
