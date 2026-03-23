# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/core/utils
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
io.py: Filesystem operations and atomic/pkecec writers.
privilege.py: systemd orchestration and root escalation wrappers.
block.py: Hardware discovery and filesystem safety checks.
units.py: Data conversion and O(1) human-readable math.
zram_stats.py: sysfs-to-model parsing for ZRAM nodes.

# Audits

### [FILE: common.py] [STUB]
Role: Command execution engine and base error hierarchy.

/DNA/: [run() -> subprocess.run()] + [stream_command() -> Popen(bufsize=1) => yield line]

- SrcDeps: None
- SysDeps:
  - subprocess
  - logging
  - dataclasses
  - typing
  - pathlib

API:
  - run(cmd, check=False) -> CmdResult: Logic-DNA runner capturing code/out/err.
  - stream_command(cmd, env, input_text) -> Iterator[str]: Line-by-line generator for live output.
  - read_file(path) -> Optional[str]: Broad-exception reader for sysfs nodes.
!Caveat: `read_file` returns None on ANY failure (permission, file missing) to maintain tool-chain robustness.


### [FILE: io.py] [STUB]
Role: Atomic and privileged file operations.

/DNA/: [pkexec_write() -> if(is_root) -> atomic_write() else -> pkexec helper]

- SrcDeps: None
- SysDeps:
  - shutil
  - tempfile
  - subprocess
  - pathlib

API:
  - atomic_write_to_file(path, content, backup) -> Tuple[bool, str]: Safely overwrites file via move.
  - pkexec_write(path, content) -> Tuple[bool, str]: Elevated write using pkexec + zman_helper.
  - sysfs_write(path, value): Direct string-write to a sysfs node.
  - is_root() -> bool: Checks os.geteuid() == 0.


### [FILE: privilege.py] [STUB]
Role: systemd orchestration and root access management.

/DNA/: [pkexec_systemctl() -> if(is_root) -> systemd_action(...) else -> pkexec helper]

- SrcDeps:
  - .common (run, SystemCommandError)
  - .io (is_root, _get_helper_path)
- SysDeps:
  - subprocess
  - pathlib

API:
  - systemd_try_restart(service) -> Tuple[bool, str]: Dual-mode restart (normal -> pkexec).
  - pkexec_daemon_reload() -> Tuple[bool, str]: Elevated daemon-reload call.
  - systemd_restart(service): Direct systemctl restart.
  - pkexec_sysctl_system(): Elevated sysctl --system application.


### [FILE: block.py] [STUB]
Role: Hardware discovery and safety validation.

/DNA/: [list_block_devices() -> run(lsblk -J) -> recurse(json) => Flat List]

- SrcDeps:
  - .common (run)
- SysDeps:
  - os
  - json
  - logging
  - pathlib

API:
  - is_block_device(path) -> bool: Verifies S_IFBLK via stat.st_mode.
  - get_device_filesystem_type(path) -> Optional[str]: Probes via blkid.
  - check_device_safety(path) -> Tuple[bool, str]: Rejects active swaps or formatted nodes.
  - list_block_devices() -> List[Dict]: Flat-array of selectable nodes.
  - get_device_scheduler(device) -> Tuple[str, List[str]]: Reads /sys/block/queue/scheduler.


### [FILE: units.py] [STUB]
Role: Data conversion and math utilities.

/DNA/: [bytes_to_human() -> math.log(1024)] + [parse_size_to_bytes() -> re.match]

- SrcDeps: None
- SysDeps:
  - re
  - math

API:
  - bytes_to_human(bytes) -> str: Returns formatted scale (K, M, G, T).
  - parse_size_to_bytes(str) -> int: Normalized parsing (GiB/GB/G -> integer).
  - calculate_compression_ratio(data, compr) -> Optional[float]: Precision-rounded ratio.


### [FILE: zram_stats.py] [STUB]
Role: Low-level sysfs parsing specialized for ZRAM.

/DNA/: [get_zram_props() -> read(mm_stat | legacy_files) => dict mapping]

- SrcDeps:
  - .common (read_file)
  - .units (bytes_to_human, calculate_compression_ratio)
- SysDeps:
  - pathlib
  - os
  - re

API:
  - scan_zram_devices() -> List[str]: Lists zram* dirs in /sys/block.
  - get_zram_props(device) -> Dict: Hydrates full state including mm_stat and bd_stat (migrated).
  - parse_zramctl_table() -> List[Dict]: Backward-compatible list of all configured devices.
  - sysfs_reset_device(path): Resets node via writing "1" to /reset path.
