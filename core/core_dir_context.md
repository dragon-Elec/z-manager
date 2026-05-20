# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/core
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
hibernation: Lifecycle orchestration for system hibernation (see hibernation_dir_context.md).
utils: Low-level system utilities (see utils_dir_context.md).
system_tuning.py: Privileged kernel parameter control (sysfs/proc).

# Audits

### [FILE: boot_config.py]
Role: Persistent system tuning (sysctl, GRUB).

/DNA/: [apply_sysctl_profile() -> pkexec_write() -> pkexec_sysctl_system()] + [set_zswap_in_grub() -> pkexec_write()]

- SrcDeps: .utils.{common, io, bootloader, kernel_cmdline, grub_paths}
- SysDeps: logging, tempfile, os, contextlib, dataclasses, pathlib

API:
  - get_swappiness() -> Optional[int]: Reads current vm.swappiness.
  - apply_sysctl_profile(enable) -> TuneResult: Toggles performance sysctl profile.
  - apply_sysctl_values(settings) -> TuneResult: Merges custom key=value pairs into config.
  - set_zswap_in_grub(enabled) -> TuneResult: Writes GRUB config to disable/enable zswap.
  - set_psi_in_grub(enabled) -> TuneResult: Writes GRUB config to enable/disable PSI.


### [FILE: config_writer.py]
Role: Configuration rendering for zram-generator.

/DNA/: [update_zram_config() -> _read_local_config() -> modify ConfigObj -> serialize to string]

- SrcDeps: .config
- SysDeps: configobj, re, io, typing, pathlib

API:
  - generate_config_string(size_formula, algorithm, priority, device, writeback_device) -> str: Direct ConfigObj rendering.
  - validate_updates(updates) -> Optional[str]: Validates size formulas and algorithm strings.
  - update_zram_config(device, updates) -> Tuple[bool, Optional[str], str]: Merges changes into config buffer.
  - update_writeback_config(device, writeback_device) -> Tuple[bool, Optional[str], str]: Specialized writeback update.
  - update_host_limit_config(device, min_ram_mb) -> Tuple[bool, Optional[str], str]: Updates host-memory-limit.
  - update_filesystem_config(device, fs_type, mount_point) -> Tuple[bool, Optional[str], str]: Updates fs-type and mount-point.
  - update_global_config(updates) -> Tuple[bool, Optional[str], str]: Modifies [zram-generator] section.
  - remove_device_from_config(device) -> Tuple[bool, Optional[str], str]: Deletes section and re-renders buffer.


### [FILE: config.py]
Role: Configuration path resolution and reading.

/DNA/: [load_effective_config() -> run(systemd-analyze cat-config) => str] + [load_effective_config_state() => EffectiveConfig(cfg, provenance)]

- SrcDeps: .utils.{common, privilege}
- SysDeps: configobj, pathlib, dataclasses, typing, io, subprocess

API:
  - get_active_config_path() -> Optional[Path]: Returns the primary config file path.
  - load_effective_config_state(root) -> EffectiveConfig: God-view with merged config and provenance tracking.
  - read_zram_config() -> ConfigObj: Reads the most specific config in the hierarchy.
  - read_global_config() -> Dict[str, str]: Returns [zram-generator] contents.
  - load_effective_config(root) -> str: Returns the raw string of the active config.
  - apply_config_with_restart(device, restart_mode) -> ConfigResult: Reloads daemon and restarts unit.


### [FILE: health.py]
Role: System health monitoring and diagnostic reports.

/DNA/: [check_system_health() -> probe commands/sysfs/swaps -> build HealthReport model]

- SrcDeps: .utils.common
- SysDeps: os, platform, dataclasses, typing

API:
  - check_system_health() -> HealthReport: Composite diagnostic of tools, nodes, and zswap.
  - get_all_swaps() -> List[SwapDevice]: Parsed snapshot of /proc/swaps entries.
  - get_zswap_status() -> ZswapStatus: Probes /sys/module/zswap.


### [FILE: hibernate_ctl.py] [DEPRECATED]
Role: Compatibility shim for core.hibernation.

/DNA/: [re-exports from .hibernation.{prober, provisioner}]

- SrcDeps: .hibernation.{prober, provisioner, types}
- SysDeps: warnings

!Caveat: update_fstab has been removed; raises NotImplementedError.


### [FILE: system_tuning.py]
Role: Privileged kernel parameter control (sysfs/proc).

/DNA/: [set_cpu_governor() -> glob /sys -> pkexec_write()] + [set_io_scheduler() -> pkexec_write()] + [set_vfs_cache_pressure() -> pkexec_write()]

- SrcDeps: .utils.{common, io}
- SysDeps: logging, pathlib, typing

API:
  - set_cpu_governor(governor, available_governors) -> bool: Sets governor for all online CPUs.
  - set_io_scheduler(device_name, scheduler, available_schedulers) -> bool: Sets I/O scheduler for block device.
  - set_vfs_cache_pressure(value) -> bool: Sets live vm.vfs_cache_pressure value.


### [FILE: zman_helper.py]
Role: Privileged helper script executed via pkexec.

/DNA/: [main() -> match argv -> cmd_exec() -> return 0/1]

- SrcDeps: None
- SysDeps: sys, os, subprocess, shutil, tempfile, json

API:
  - is_path_allowed(path) -> bool: Security whitelist check for write operations.
  - is_service_allowed(service) -> bool: Security whitelist check for systemctl operations.
  - cmd_write(path) -> int: Atomic write with security whitelist (reads from stdin).
  - cmd_hibernate_setup() -> int: Master transaction for full hibernation setup (JSON plan from stdin).
  - cmd_systemctl(action, service) -> int: Privileged unit control (daemon-reload, start, stop, enable, disable).


