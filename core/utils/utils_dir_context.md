# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/core/utils
Low-level system utility suite. Acts as the modularized engine for all OS-level operations (I/O, execution, hardware discovery, and systemd/pkexec orchestration).

# Rules
!Rule: [Atomic Writes for Configs] - Reason: System files (/etc/) must be written atomically to ensure partial writes don't corrupt system state.
!Rule: [Root Preference] - Reason: If already running as root (euid=0), skip pkexec escalation to avoid unnecessary shell forks.

# Atomic Notes
!Pattern: [Sub-module Isolation] - Reason: Granular division of logic (common, io, block, units) minimizes Circular Import risk during scaling.
!Decision: [sysfs > zramctl] - Reason: Directly parsing /sys/block/zramN/ ensures compatibility across kernel versions where zram-tools might be missing.

# Index
__init__.py: Internal entry point; no exports.
common.py: Core runner and shared exceptions.
io.py: Filesystem operations and atomic/pkexec writers.
privilege.py: systemd orchestration and root escalation wrappers.
block.py: Hardware discovery and filesystem safety checks.
bootloader.py: Bootloader and initramfs detection.
grub_paths.py: Centralized GRUB/sysctl paths and constants.
kernel_cmdline.py: Kernel command-line parsing.
swap.py: Swap device detection and parsing.
units.py: Data conversion and O(1) human-readable math.
zram_stats.py: sysfs-to-model parsing for ZRAM nodes.

# Audits

### [FILE: common.py]
Role: Command execution engine and base error hierarchy.

/DNA/: [run() -> subprocess.run()] + [stream_command() -> Popen(bufsize=1) => yield line]

- SrcDeps: None
- SysDeps: subprocess, logging, dataclasses, typing, pathlib

API:
  - run(cmd, check, env) -> CmdResult: Logic-DNA runner capturing code/out/err.
  - stream_command(cmd, env, input_text) -> Iterator[str]: Line-by-line generator for live output.
  - read_file(path) -> str | None: Broad-exception reader for sysfs nodes.
!Caveat: `read_file` returns None on ANY failure (permission, file missing) to maintain tool-chain robustness.


### [FILE: io.py]
Role: Atomic and privileged file operations.

/DNA/: [pkexec_write() -> if(is_root) -> atomic_write() else -> pkexec helper]

- SrcDeps: None
- SysDeps: shutil, tempfile, subprocess, pathlib

API:
  - atomic_write_to_file(file_path, content, backup) -> tuple[bool, str | None]: Safely overwrites file via move.
  - pkexec_write(file_path, content) -> tuple[bool, str | None]: Elevated write using pkexec + zman_helper.
  - sysfs_write(path, value): Direct string-write to a sysfs node.
  - is_root() -> bool: Checks os.geteuid() == 0.


### [FILE: privilege.py]
Role: systemd orchestration and root access management.

/DNA/: [pkexec_systemctl() -> if(is_root) -> systemd_action(...) else -> pkexec helper]

- SrcDeps: .common, .io
- SysDeps: subprocess, pathlib

API:
  - systemd_daemon_reload(): Run systemctl daemon-reload.
  - systemd_restart(service): Run systemctl restart.
  - pkexec_daemon_reload() -> tuple[bool, str | None]: Elevated daemon-reload call.
  - pkexec_systemctl(action, service) -> tuple[bool, str | None]: Elevated systemctl action.
  - systemd_try_restart(service) -> tuple[bool, str | None]: Dual-mode restart (normal -> pkexec).
  - pkexec_sysctl_system() -> tuple[bool, str | None]: Elevated sysctl --system application.


### [FILE: block.py]
Role: Hardware discovery and safety validation.

/DNA/: [list_block_devices() -> run(lsblk -J) -> recurse(json) => Flat List]

- SrcDeps: .common
- SysDeps: os, json, logging, pathlib

API:
  - is_block_device(path) -> bool: Verifies S_IFBLK via stat.st_mode.
  - get_device_filesystem_type(path) -> Optional[str]: Probes via blkid.
  - check_device_safety(path) -> Tuple[bool, str]: Rejects active swaps or formatted nodes.
  - list_block_devices() -> List[Dict]: Flat-array of selectable nodes.
  - get_device_scheduler(device) -> Tuple[str, List[str]]: Reads /sys/block/queue/scheduler.


### [FILE: bootloader.py]
Role: Bootloader and initramfs detection.

/DNA/: [detect_bootloader() -> shutil.which | os.path.exists] + [detect_initramfs_system() -> os.path.isdir | shutil.which]

- SrcDeps: None
- SysDeps: os, shutil

API:
  - detect_bootloader() -> str: Returns 'grub', 'systemd-boot', or 'unknown'.
  - detect_initramfs_system() -> str: Returns 'initramfs-tools', 'dracut', 'mkinitcpio', or 'unknown'.


### [FILE: grub_paths.py]
Role: Centralized GRUB/sysctl path and content constants.

/DNA/: [None (Constant Repository)]

- SrcDeps: None
- SysDeps: pathlib

API:
  - GRUB_ZSWAP_DISABLE_PATH, GRUB_RESUME_CONFIG_PATH, SYSCTL_CONFIG_PATH: Path objects.
  - SYSCTL_DEFAULT_SETTINGS, SYSCTL_GAMING_PROFILE: Tuning profile content strings.
  - ZMAN_HELPER_ALLOWED_PATHS: Security whitelist of paths help is allowed to write.


### [FILE: kernel_cmdline.py]
Role: Kernel command-line parsing.

/DNA/: [is_kernel_param_active() -> read(/proc/cmdline) -> any(startswith)]

- SrcDeps: .common
- SysDeps: logging

API:
  - is_kernel_param_active(param) -> bool: Checks for parameter presence in live boot session.


### [FILE: swap.py]
Role: Swap device detection and parsing.

/DNA/: [get_all_swaps() -> read(/proc/swaps) -> list(SwapDevice)] + [detect_resume_swap() -> find first non-zram swap]

- SrcDeps: .common
- SysDeps: os, dataclasses, pathlib, typing

API:
  - get_all_swaps() -> list[SwapDevice]: Parsed snapshot of active swaps.
  - is_device_active(device_path) -> bool: Verifies if path is active in swaps or mounts.
  - is_device_in_swaps(device_name) -> bool: Namespace-specific swap check.
  - detect_resume_swap() -> Optional[str]: Identifies suitable physical device for resume.


### [FILE: units.py]
Role: Data conversion and math utilities.

/DNA/: [bytes_to_human() -> math.log(1024)] + [parse_size_to_bytes() -> re.match]

- SrcDeps: None
- SysDeps: re, math

API:
  - bytes_to_human(size_bytes) -> str: Returns formatted scale (K, M, G, T).
  - parse_size_to_bytes(size_str) -> int: Normalized parsing (GiB/GB/G -> integer).
  - calculate_compression_ratio(data_size, compr_size) -> float | None: Computes ratio from size strings.


### [FILE: zram_stats.py]
Role: Low-level sysfs parsing specialized for ZRAM.

/DNA/: [get_zram_props() -> read(mm_stat | legacy_files) => dict mapping]

- SrcDeps: .common, .units
- SysDeps: pathlib, os, re

API:
  - scan_zram_devices() -> list[str]: Lists zram* devices in /sys/block.
  - zram_sysfs_dir(device_name) -> str: Returns base sysfs path.
  - sysfs_reset_device(device_path): Resets device via sysfs node.
  - get_zram_mountpoint(device_name) -> str: Returns mountpoint or [SWAP].
  - get_zram_props(device_name) -> dict[str, Any]: Hydrates full state including mm_stat and bd_stat.
  - parse_zramctl_table() -> list[dict[str, Any]]: Composite list of all configured devices.
