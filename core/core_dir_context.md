# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/core
The engine room of Z-Manager. Handles low-level OS interactions (sysfs, systemd, GRUB), ZRAM configuration (zram-generator), system health monitoring, and persistent kernel tuning.

# Rules
!Rule: [No direct system mutation from UI] - Reason: Logic must flow through core modules which handle validation and safety checks (e.g., FS detection).

# Atomic Notes
!Pattern: [Atomic Writes] - Reason: All system config changes use atomic_write_to_file to prevent corruption.
!Decision: [Privilege Escalation via pkexec] - Reason: The UI runs as user; privileged tasks use pkexec + zman_helper.py for targeted root access.
!Pattern: [ConfigObj for INI] - Reason: Preserves user comments and formatting in zram-generator.conf.

# Index
__init__.py: Currently empty; placeholder for future core re-exports.
device_management: Lifecycle orchestration for ZRAM devices (see device_management_dir_context.md).

# Audits

### [FILE: os_utils.py]
Role: Low-level system utilities and execution wrappers.

/DNA/: [run() -> subprocess.run()] + [pkexec_write() -> subprocess.run(pkexec, zman-helper)]

- SrcDeps: None
- SysDeps:
  - subprocess
  - os
  - shutil
  - tempfile
  - re
  - dataclasses
  - pathlib
  - logging
  - typing

API:
  - run(cmd, check=False) -> CmdResult: Standard command runner capturing stdout/err.
  - stream_command(cmd, env, input_text) -> Iterator[str]: Generator for real-time command output.
  - is_block_device(path) -> bool: Determine if path refers to a block device.
  - read_file(path) -> Optional[str]: Safely reads a sysfs file.
  - sysfs_write(path, value): Safely writes to a sysfs file.
  - zram_sysfs_dir(device_name) -> str: Resolves /sys/block/zramN path.
  - pkexec_write(path, content) -> Tuple[bool, str]: Privileged atomic write via helper.
  - pkexec_daemon_reload() -> Tuple[bool, str]: Privileged systemd reload.
  - pkexec_systemctl(action, service) -> Tuple[bool, str]: Privileged unit control.
  - check_device_safety(path) -> Tuple[bool, str]: Validates dev has no FS and is not active swap/mount.
  - is_device_active(device_path) -> bool: Check if device is used as swap or mounted.
  - list_block_devices() -> List[Dict]: Flat list of all selectable nodes using lsblk.
  - get_device_scheduler(device_name) -> Tuple[str, List[str]]: Reads IO scheduler state.
  - set_device_scheduler(device_name, scheduler) -> bool: Sets IO scheduler state.
  - get_device_filesystem_type(device_path) -> Optional[str]: Detects FS signature via blkid.
  - sysfs_reset_device(device_path): Resets zram device via sysfs to avoid node deletion.
  - systemd_try_restart(service) -> Tuple[bool, str]: Safe service restart with error capture.
  - parse_zramctl_table() -> List[Dict]: Modern sysfs-based device prober.
  - parse_size_to_bytes(size_str) -> int: Normalized size parsing (G, M, K).
  - is_root() -> bool: Checks for root privileges.
  - atomic_write_to_file(path, content, backup) -> Tuple[bool, str]: Safe file overwrite with diff-check.


### [FILE: boot_config.py]
Role: Persistent system tuning (sysctl, GRUB, initramfs).

/DNA/: [apply_sysctl_profile() -> atomic_write() -> sysctl --system] + [update_grub_resume() -> atomic_write(/etc/default/grub.d/)]

- SrcDeps:
  - .os_utils (run, SystemCommandError, atomic_write_to_file, read_file)
- SysDeps:
  - logging
  - tempfile
  - os
  - shutil
  - contextlib
  - dataclasses
  - pathlib

API:
  - is_kernel_param_active(param) -> bool: Checks /proc/cmdline for active boot params.
  - get_swappiness() -> Optional[int]: Reads current vm.swappiness.
  - apply_sysctl_profile(enable) -> TuneResult: Toggles performance sysctl profile.
  - apply_sysctl_values(settings) -> TuneResult: Merges custom key=value pairs into config.
  - set_zswap_in_grub(enabled) -> TuneResult: Writes GRUB config to disable/enable zswap.
  - set_psi_in_grub(enabled) -> TuneResult: Writes GRUB config to enable/disable PSI.
  - detect_bootloader() -> str: Identifies grub vs systemd-boot.
  - update_grub_resume(uuid, offset) -> TuneResult: Persists resume parameters to GRUB.
  - detect_initramfs_system() -> str: Identifies initramfs-tools, dracut, or mkinitcpio.
  - configure_initramfs_resume(uuid, offset) -> TuneResult: Persists resume parameters to initramfs-tools.
  - regenerate_initramfs() -> TuneResult: System-agnostic initramfs update.


### [FILE: config_writer.py]
Role: Configuration rendering for zram-generator.

/DNA/: [update_zram_config() -> read_zram_config() -> modify ConfigObj -> serialize to string]

- SrcDeps:
  - .config (CONFIG_PATH)
- SysDeps:
  - configobj
  - re
  - io
  - typing
  - pathlib

API:
  - generate_config_string(size, algo, priority, device, writeback) -> str: Direct ConfigObj rendering.
  - validate_updates(updates) -> Optional[str]: Validates size formulas and algo strings.
  - update_zram_config(device, updates) -> Tuple[bool, str, str]: Merges changes into config buffer with validation.
  - update_writeback_config(device, writeback_device) -> Tuple[bool, str, str]: Specialized writeback update.
  - update_host_limit_config(device, min_ram_mb) -> Tuple[bool, str, str]: Updates host-memory-limit.
  - update_filesystem_config(device, fs_type, mount_point) -> Tuple[bool, str, str]: Updates fs-type and mount-point.
  - update_global_config(updates) -> Tuple[bool, str, str]: Modifies [zram-generator] section.
  - remove_device_from_config(device) -> Tuple[bool, str, str]: Deletes section and re-renders entire buffer.


### [FILE: config.py]
Role: Configuration path resolution and reading.

/DNA/: [read_zram_config() -> hierarchy search -> ConfigObj(path)]

- SrcDeps:
  - .os_utils (run, systemd_daemon_reload, systemd_try_restart, SystemCommandError)
- SysDeps:
  - configobj
  - pathlib
  - dataclasses
  - typing
  - io
  - subprocess

API:
  - get_active_config_path() -> Optional[Path]: Resolves first existing config in hierarchy.
  - read_zram_config() -> ConfigObj: Reads the most specific config in the hierarchy.
  - read_global_config() -> Dict: Returns [zram-generator] contents.
  - load_effective_config() -> str: Returns the raw string of the active config.
  - apply_config_with_restart(device, restart_mode) -> ConfigResult: Reloads daemon and restarts unit.


### [FILE: health.py]
Role: System health monitoring and diagnostic reports.

/DNA/: [check_system_health() -> probe commands/sysfs/swaps -> build HealthReport model]

- SrcDeps:
  - .os_utils (run)
- SysDeps:
  - os
  - platform
  - dataclasses
  - typing

API:
  - check_system_health() -> HealthReport: Composite diagnostic of tools, nodes, and zswap.
  - get_all_swaps() -> List[SwapDevice]: Parsed snapshot of /proc/swaps entries.
  - get_zswap_status() -> ZswapStatus: Probes /sys/module/zswap.


### [FILE: hibernate_ctl.py]
Role: Swapfile/partition management for hibernation.

/DNA/: [create_swapfile() -> truncate+chattr+C (btrfs) -> fallocate -> mkswap -> UUID/offset]

- SrcDeps:
  - .os_utils (run, SystemCommandError, atomic_write_to_file, read_file, check_device_safety, is_block_device, pkexec_write, is_root)
- SysDeps:
  - logging
  - os
  - re
  - shlex
  - shutil
  - dataclasses
  - pathlib
  - typing

API:
  - check_hibernation_readiness() -> HibernateCheckResult: Secure Boot and RAM vs Swap capacity check.
  - get_memory_info() -> Tuple[int, int]: Reads RAM and Swap total from /proc/meminfo.
  - create_swapfile(path, size_mb) -> SwapCreationResult: Robust swapfile creation (Nocow if Btrfs).
  - get_resume_offset(path) -> Optional[int]: Calculates filefrag/btrfs physical offset.
  - get_partition_uuid(path) -> Optional[str]: Resolves device UUID for kernel params.
  - enable_swapon(path, priority) -> bool: Activates swap on direct path.
  - update_fstab(device_path, uuid) -> bool: Safely appends entry to /etc/fstab with nofail.


### [FILE: zman_helper.py]
Role: Privileged helper script executed via pkexec.

/DNA/: [main() -> match argv -> cmd_exec() -> return 0/1]

- SrcDeps: None (Stand-alone)
- SysDeps:
  - sys
  - os
  - subprocess
  - shutil
  - tempfile

API:
  - cmd_write(path): Atomic write with security whitelist check.
  - cmd_daemon_reload(): Privileged systemd reload.
  - cmd_systemctl(action, service): Privileged unit control.
  - cmd_live_apply(device, config_path): Batched lifecycle: Stop -> Write -> Reload -> Restart.
  - cmd_live_remove(device, config_path): Batched lifecycle: Stop -> Write -> Reload.


