# CoGOS Hardware Veto Contract

Doctrine: hardware enforces; software proposes.

CoGOS treats the operating system, runtime, sigils, manifests, and AI layers as untrusted from the perspective of physical safety. They may observe, validate, hash, reject, and report. They are not the final authority.

## Required Physical Authority

The physical veto layer must be able to perform these actions without permission from Linux, Python, the runtime, or any model:

- cut power
- halt execution
- freeze the bus
- lock the disk
- drop the network
- kill the process

## Out-of-Band Requirements

The fail-safe must use a separate power rail, microcontroller, bus, firmware image, and clock. It must not run Linux, Python, an LLM, a VM, dynamic code, or a general scheduler.

## CoGOS Software Boundary

The CoGOS runtime exposes only a report-only interface:

```sh
cogos-hardware-veto status
cogos-hardware-veto verify
cogos-hardware-veto proof
cogos-hardware-veto report anomaly_detected --severity warn
```

These commands prove the software contract and write audit events. They do not cut power, disable the veto, or emulate the physical controller.

## Hardware Attachment Proof

Until a real microcontroller bridge is installed, CoGOS reports `attached=false` and `deployment_ready=false`. A hardware bridge may publish a heartbeat to:

```text
/opt/cogos/memory/hardware_veto/HEARTBEAT
```

and an attachment marker to:

```text
/opt/cogos/memory/hardware_veto/ATTACHED
```

Those files are hints for operator visibility only. They are not authority.

## Ship Rule

An ISO may pass internal software preflight when the contract is valid, but a production safety claim requires physical hardware proof. No CoGOS software component is allowed to claim it is the final safety mechanism.
