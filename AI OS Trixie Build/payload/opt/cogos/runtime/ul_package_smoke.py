"""Smoke: UL package ecosystem."""

from __future__ import annotations

from ul_package_manager import install_ul_package, list_ul_packages, remove_ul_package, verify_catalog


def main() -> int:
    verify = verify_catalog()
    assert verify["ok"], verify

    listed = list_ul_packages()
    assert any(p["id"] == "community.hello_ul" for p in listed)

    inst = install_ul_package("community.hello_ul", profile_id="operator")
    assert inst["ok"], inst

    rem = remove_ul_package("community.hello_ul", profile_id="operator")
    assert rem["ok"], rem

    print("ul_package_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
