// SPDX-License-Identifier: GPL-2.0
/*
 * cog_k32_chardev_stub.c — out-of-tree char device transport for CoGOS K32
 *
 * This module is NOT shipped in the Debian remaster. It documents the kernel
 * boundary: validate k_layer, log caller, forward payload to userspace via
 * netlink/chardev. Install separately when building a custom kernel.
 *
 * Userspace peer: cogos-k32-forward (runtime/k32_forward_daemon.py)
 * Socket fallback: /run/cogos/k32.sock
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/cog_k32.h>

#define COG_K32_DEV_NAME "cog_k32"
#define COG_K32_IOCTL_CALL	_IOW('C', 1, struct k32_payload)
#define COG_K32_IOCTL_STATUS	_IOR('C', 2, struct k32_payload)

static long cog_k32_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct k32_payload payload;
	int k_layer = 0;

	switch (cmd) {
	case COG_K32_IOCTL_CALL:
		if (copy_from_user(&payload, (void __user *)arg, sizeof(payload)))
			return -EFAULT;
		/* k_layer passed via filp->private_data or extended ioctl — stub only */
		if (payload.size < sizeof(payload) || payload.size > 4096)
			return -EINVAL;
		/* Forward to userspace daemon — not implemented in stub build */
		return -EDEFER;
	case COG_K32_IOCTL_STATUS:
		return 0;
	default:
		return -ENOTTY;
	}
}

static const struct file_operations cog_k32_fops = {
	.owner		= THIS_MODULE,
	.unlocked_ioctl	= cog_k32_ioctl,
	.llseek		= noop_llseek,
};

static int __init cog_k32_init(void)
{
	pr_info("cog_k32: chardev stub loaded (userspace forward required)\n");
	return 0;
}

static void __exit cog_k32_exit(void)
{
	pr_info("cog_k32: chardev stub unloaded\n");
}

module_init(cog_k32_init);
module_exit(cog_k32_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("CoGOS K32 semantic control plane transport stub");
