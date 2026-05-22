# Install Proof — Metal Validation (Phase A.1)

After a lab-disk install, capture one proof bundle to archive beside the ISO.

## Capture (on installed or live system)

```sh
cogos-install-proof capture --target /dev/sdX --label metal-laptop-1
```

Writes:

- `/opt/cogos/memory/logs/install_proof_bundle.json` (latest)
- `/opt/cogos/memory/logs/install_proof_bundles/<label>-<timestamp>/`

## Verify

```sh
cogos-install-proof verify
```

## Metal checklist

```sh
cogos-install-proof checklist
```

Manual steps (live boot, apply install, reboot, desktop) are listed with `?` until you complete them on hardware.

## Recommended flow

1. `cogos-install plan --target /dev/sdX --json`
2. `cogos-install validate --target /dev/sdX --json`
3. `cogos-install apply --target /dev/sdX --yes --confirm-erase sdX` (spare disk only)
4. Reboot from disk
5. `cogos-persist status`
6. `cogos-pid1-proof`
7. `cogos-eval run`
8. `cogos-install-proof capture --label post-install`

Copy the bundle directory to your ISO proof folder on the build host.
