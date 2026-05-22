#ifndef _LINUX_COG_K32_H
#define _LINUX_COG_K32_H

#include <linux/types.h>

/*
 * cog_k32 — CoGOS semantic control plane shim
 *
 * This is NOT a kernel primitive. The kernel:
 *   - validates k_layer in [1..32]
 *   - validates payload pointer
 *   - logs PID + timestamp
 *
 * All semantics, invariants, and allow/deny decisions are handled
 * in the CoGOS runtime (LawPulse) in userspace.
 *
 * Return values:
 *   0        accepted by shim, forwarded to CoGOS runtime
 *  -EPERM    k_layer requires operator consent; none present
 *  -EINVAL   malformed payload or k_layer out of range
 *  -EDEFER   CoGOS runtime deferred; check Pattern Ledger
 */

struct k32_payload {
	__u32 size;
	__u32 op_code;
	__u64 arg0;
	__u64 arg1;
	__u64 arg2;
	__u64 reserved;
};

int cog_k32(int k_layer, struct k32_payload *payload);

#endif /* _LINUX_COG_K32_H */
