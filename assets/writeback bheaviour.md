Based on my research, I can provide a comprehensive answer about setting a writeback device on an active zram device.

# Setting Writeback Device on Active Zram Device

**No, it is not possible to set a writeback device on an active zram device.** The backing device must be configured **before** the zram device is initialized with a disksize.

## Key Requirements and Limitations

### Timing Constraints

The Linux kernel documentation clearly states that the backing device must be set up **before disksize setting**. Once a zram device has been initialized (disksize has been set), attempting to modify the `backing_dev` attribute will result in an `-EBUSY` error, indicating that the device is busy and cannot accept configuration changes.[1]

### Proper Setup Sequence

The correct sequence for configuring zram with a writeback device is:[1]

1. **Load the zram module**: `modprobe zram`
2. **Set compression algorithm** (optional): `echo zstd > /sys/block/zram0/comp_algorithm`
3. **Set backing device**: `echo /dev/sda5 > /sys/block/zram0/backing_dev`
4. **Set disksize**: `echo 1G > /sys/block/zram0/disksize`
5. **Format and activate**: `mkswap /dev/zram0 && swapon /dev/zram0`

### Technical Limitations

According to the kernel documentation's error handling section, attempts to modify attributes that cannot be changed once the device has been initialized will return `-EBUSY` with the message "an attempt to modify an attribute that cannot be changed once the device has been initialised. Please reset device first".[1]

## Workaround: Device Reset

If you need to add a writeback device to an already active zram device, you must:

1. **Deactivate the device**: `swapoff /dev/zram0` (if used as swap)
2. **Reset the device**: `echo 1 > /sys/block/zram0/reset`
3. **Reconfigure with backing device**: Follow the proper setup sequence above
4. **Reactivate**: Format and mount/swapon the device again

Note that resetting the device will **destroy all data** stored in the zram device.[1]

## Backing Device Requirements

The backing device must be:[2][1]
- A **partition** (not a regular file or loop device in most cases)
- **Available and not in use** by other systems (LVM, filesystem, etc.)
- **Unmounted and not active** as swap or other storage

## Modern Tools Support

Tools like `zram-generator` support configuring writeback devices through configuration files, but they handle the proper initialization sequence automatically. The writeback feature is available but requires proper daemon management for optimal utilization, as the writeback process itself requires manual triggering through commands like `echo idle > /sys/block/zram0/writeback`.[3][4]

The limitation exists because the kernel needs to establish the relationship between the zram device and its backing storage during the initial setup phase, and changing this relationship after initialization would compromise data integrity and device consistency.



research 2-

The error “Permission denied” when trying to write to `/sys/class/zram-control/hot_add` arises because only the root user (not just sudo-ed commands for individual tools, but an actual root shell or direct root-level command) can write to sysfs files like this one. While `sudo tee` elevates permissions for the `tee` process, the shell's redirection (n (echo 0 | ...) isn't fully executed as root, resulting in permission issues[1]. Additionally, for zram, device addition is usually done by *reading* (`cat /sys/class/zram-control/hot_add`), not writing with echo, as per the official kernel and ArchWiki documentation[2][3]. 

### Correct Way to Add ZRAM Device

- To add a zram device: run `cat /sys/class/zram-control/hot_add` (not echo) as root, which returns the device ID, then configure it using the appropriate sysfs paths.[2][4]
- Writing with echo is intended for `hot_remove` but not for `hot_add` on most kernels.[2]
- For operations requiring writing, use a root shell with `sudo -i` or prefix commands with `sudo bash -c '...'`, but for zram hot_add, explicit writing is not the intended usage on modern Linux kernels.[1][2]

### Common Pitfalls and Solutions

- Even with `sudo tee`, permission is denied since the kernel restricts sysfs writes to actual root processes.[1]
- If you’re trying to use zram-generator or zramctl, ensure configuration files are set up properly, and generally prefer using `cat` to trigger device creation, then configure compression and disksize, and enable with `swapon`.[5][2]
- If the device still does not appear, rebooting can help, or review system logs with `journalctl -xe` or `dmesg` for kernel loading/syfs access errors.[6]

### Example Steps
- Load module: `sudo modprobe zram`
- Add a device: `cat /sys/class/zram-control/hot_add`
- Configure it:  
  - `echo zstd > /sys/block/zram0/comp_algorithm`  
  - `echo 4G > /sys/block/zram0/disksize`
- Initialize swap: `sudo mkswap /dev/zram0`
- Enable swap: `sudo swapon /dev/zram0`[7][2]

In summary, you’re seeing “Permission denied” because echoing into `hot_add` is not allowed—the correct workflow is to read from it with root privileges instead.[4][2][1]


Yes, a writeback device can be set for zram on a running system, provided that the kernel has `CONFIG_ZRAM_WRITEBACK` enabled and the zram device has not had its disksize set yet. The writeback device is set by writing the device path (must be a partition, like `/dev/sdXn` or `/dev/nvmeXnY`) to `/sys/block/zramX/backing_dev` before setting the disksize for that zram device.[2][5][7]

### Key Facts and Workflow

- The writeback device must be associated *before* setting the zram device’s disksize; otherwise, you must reset the zram device before changing the backing device.[7][2]
- The workflow for a running system:
  - Detach (reset) and reconfigure the zram device if it had previous disksize set:
    - `echo 1 > /sys/block/zramX/reset`
    - `echo "/dev/sda5" > /sys/block/zramX/backing_dev`
    - `echo 4G > /sys/block/zramX/disksize`
  - Afterwards, idle/incompressible pages can be written back with commands to `/sys/block/zramX/writeback`.[5][2][7]

### Using zramctl

- `zramctl` is used to quickly configure and query zram devices, but for writeback, setting the backing device is done via sysfs, not directly by `zramctl`.[8]
- After configuring via sysfs, `zramctl` can show the device status, but does not set writeback devices itself.[8]

### Practical Notes

- You can issue writeback operations and limits live on a running system after device configuration.[2][5][7]
- Changing the writeback (backing) device itself on a running zram device requires a reset, and then repeating the setup sequence.[7][2]

In summary, you can set a writeback device with zram on a live system, but if the zram device is already in use, reset it first, then set the backing device, disksize, and reinitialize swap if needed.[2][7][8]


A writeback device for zram cannot be set using `zramctl`; instead, it is set directly via the sysfs interface by writing the backing device path to `/sys/block/zramX/backing_dev` using root privileges. No user-space utility currently offers direct support for setting the writeback device—this operation must be performed manually through sysfs.[1][2][3]

### Setting a Writeback Device: Steps

- Reset the zram device first (if it is already configured):
  - `echo 1 | sudo tee /sys/block/zram0/reset`[4]
- Set the writeback device via sysfs using root:
  - `echo /dev/sdXY | sudo tee /sys/block/zram0/backing_dev` (replace `/dev/sdXY` with your partition)[1]
- Set the disksize and configure other parameters as needed.

### Tools Involved

- Only the shell with root privileges and `tee`, or by running `sudo bash -c "echo ... > ..."` can set this value.[2][1]
- Utilities like `zramctl`, `systemd-zram-generator`, or `zram-config` do not provide a way to set the writeback device through their commands or config files at this time.[3][2]
- Some distros or scripts may automate this via startup scripts, but they still use sysfs writing under the hood.

In summary, setting a zram writeback device always involves echoing or writing the device path to `/sys/block/zramX/backing_dev` as root, not using a high-level tool.[1][2][3]

Older versions of `zramctl`, such as the one present in Ubuntu Jammy (22.04) — typically util-linux around version 2.34 to 2.38 — do not have the capability to show or configure the writeback (backing) device for zram directly. The writeback device support is still managed through sysfs at `/sys/block/zramX/backing_dev` and is not exposed as an option or status field in older `zramctl` versions in Ubuntu Jammy.[1][2]

### Summary:
- Ubuntu Jammy’s `zramctl` does **not** show or manage the writeback device since the feature was not integrated into the tool at that time.[2][1]
- Writeback device info and configuration must be checked and done manually via sysfs interface.
- Newer zram kernel features for writeback (CONFIG_ZRAM_WRITEBACK) and related tooling improvements appeared after Ubuntu Jammy’s release, so full support in utilities like `zramctl` came later or remains manual.[3][4]

So, on Ubuntu Jammy, to work with writeback devices, one uses manual sysfs commands and not `zramctl` for that functionality.Older versions of zramctl like the one in Ubuntu Jammy (22.04) do not show or handle the writeback (backing) device feature directly. The writeback device must be configured and viewed via the sysfs interface at /sys/block/zramX/backing_dev manually, as the feature and its integration into zramctl came after the Ubuntu Jammy release. Therefore, zramctl in Ubuntu Jammy does not display or set writeback devices; this is done only via manual sysfs operations with root privileges.[4][1][3][2]