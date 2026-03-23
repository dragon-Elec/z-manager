# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/core/device_management
Handles ZRAM device lifecycle: discovery, state probing, kernel node provisioning, and configuration orchestration.

# Rules
!Rule: [Force for active devices] - Reason: Configurator requires explicit force=True for reset/reconfigure if device is in swap/mount.

# Atomic Notes
!Pattern: [Read-Oriented Separation] - Reason: prober is read-only ("Safe Zone"); provisioner is destructive ("Hazard Zone").
!Decision: [hot_add usage] - Reason: Kernel's zram-control/hot_add creates nodes dynamically without module reload.

# Index
__init__.py: Exposes no public exports directly; use submodule imports.

# Audits

### [FILE: types.py]
Role: Shared data structures and models for device management.

/DNA/: [dataclasses(frozen=True) => model snapshots of state/results]

- SrcDeps: None
- SysDeps:
  - dataclasses
  - typing

API:
  - DeviceInfo: Complete state snapshot (name, size, algo, etc).
  - WritebackStatus: Live backing dev stats snapshot.
  - UnitResult/PersistResult/OrchestrationResult: Multi-step operation outcomes.
  - Action: Atomic orchestration step.
  - WritebackResult: Result of live writeback configuration.


### [FILE: prober.py]
Role: Read-only detection and sysfs probing.

/DNA/: [parse_zramctl_table() => List[DeviceInfo]] + [_get_sysfs() => raw node value]

- SrcDeps:
  - .types
  - core.os_utils (run, SystemCommandError, is_block_device, zram_sysfs_dir, parse_zramctl_table, read_file, NotBlockDeviceError)
- SysDeps:
  - typing

API:
  - list_devices() -> List[DeviceInfo]: Probes all active ZRAM devices.
  - get_writeback_status(device_name) -> WritebackStatus: Live backing dev stats.
  - is_device_active(device_name) -> bool: Checks /proc/swaps and mount.
  - read_params_best_effort(device_name, default_size) -> dict: Extracts current disksize/algo.


### [FILE: provisioner.py]
Role: Destructive kernel node management and resets.

/DNA/: [ensure_device_exists() -> modprobe/hot_add] + [reconfigure_device_sysfs() -> reset -> sysfs_write(all)]

- SrcDeps:
  - .types
  - core.os_utils (run, SystemCommandError, sysfs_write, zram_sysfs_dir, sysfs_reset_device, read_file, ValidationError, is_block_device)
- SysDeps:
  - os
  - logging
  - typing

API:
  - ensure_device_exists(device_name) -> None: Guarantees /dev/zramN via hot_add.
  - reconfigure_device_sysfs(device_name, size, algorithm, streams, backing_dev) -> None: Force-resets and rewrites sysfs nodes.
  - reset_device(device_name, confirm) -> UnitResult: Safely resets device to 0 bytes.


### [FILE: configurator.py]
Role: High-level orchestration, persistence, and service management.

/DNA/: [update_config() -> pkexec_write() -> daemon-reload -> restart_unit]

- SrcDeps:
  - .types
  - .prober
  - .provisioner
  - core.os_utils (run, SystemCommandError, ValidationError, NotBlockDeviceError, is_block_device, pkexec_write, pkexec_daemon_reload, pkexec_systemctl, atomic_write_to_file, systemd_daemon_reload, systemd_try_restart, systemd_restart, check_device_safety)
  - core.config (CONFIG_PATH, read_zram_config)
  - core.config_writer (update_zram_config, update_global_config, remove_device_from_config)
- SysDeps:
  - logging
  - typing

API:
  - apply_device_config(device_name, config_updates, restart_service, reload_daemon) -> UnitResult: Saves config and optionally applies it.
  - apply_global_config(updates) -> UnitResult: Updates global [zram-generator] settings.
  - remove_device_config(device_name, apply_now) -> UnitResult: Deletes device config and optionally stops service.
  - set_writeback(device_name, writeback_device, force, create_if_missing, default_size, new_size) -> WritebackResult: Live application of backing store.
  - clear_writeback(device_name, force, create_if_missing, default_size, new_size) -> WritebackResult: Resets and removes backing store live.
  - persist_writeback(device_name, writeback_device, apply_now) -> PersistResult: Saves writeback config to disk.
  - restart_unit_for_device(device_name) -> UnitResult: Restarts setup service.
  - restart_device_unit(device_name, mode) -> UnitResult: Robust service restart (try/force/none).
  - ensure_writeback_state(device_name, desired_writeback, force, restart_mode) -> OrchestrationResult: Idempotently matches live device to desired state.
