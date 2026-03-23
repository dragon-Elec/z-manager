# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/tests/integration
High-level integration tests for Z-Manager. These tests verify the end-to-end orchestration of ZRAM devices, including persistent configuration with `systemd-zram-generator`, writeback device management, and block device safety checks.

# Rules
!Rule: [Run as Root] - Reason: Integration tests mutate real system state (ZRAM nodes, systemd services, `/etc` files) and require `sudo`.

# Atomic Notes
!Pattern: [Mocked vs. Real System] - Reason: Some tests (e.g., `test_safety.py`) use `BaseTestCase` but interact with real device nodes, while others are standalone scripts that invoke shell commands directly.
!Decision: [Loop Device for WB] - Reason: `test_persistence.py` and `test_modifications.py` use `losetup` to create virtual backing devices for testing writeback functionality without needing physical disks.

# Index
__init__.py: Package marker for test discovery.

# Audits

### [FILE: test_modifications.py] [WIP]
Role: End-to-end testing of live writeback attachment and device resets.

/DNA/: [set_writeback(zram, wb) -> verify_status -> clear_writeback() -> verify_reset_device()]

- SrcDeps: core.device_management{configurator, provisioner, prober}, core.os_utils{ValidationError, NotBlockDeviceError}
- SysDeps: os, sys, sudo, mkswap, swapon, swapoff

API:
  - run_all_tests(zram_dev, wb_dev): Sequentially executes writeback attachment, detachment, and device resetting.


### [FILE: test_persistence.py] [WIP]
Role: Validation of `zram-generator.conf` persistence and service recreation.

/DNA/: [persist_writeback(apply_now=True) -> verify_config_written -> restart_service -> verify_live_restore]

- SrcDeps: core.device_management.configurator{persist_writeback, ensure_writeback_state}, core.device_management.prober.get_writeback_status, core.os_utils.sysfs_reset_device, core.config.CONFIG_PATH
- SysDeps: configparser, losetup, systemctl, swapoff

API:
  - test_persist_and_recreate(zram_dev, wb_dev): Simulates a "reboot" by resetting nodes and restarting systemd units to verify auto-restore.


### [FILE: test_queries.py] [WIP]
Role: CLI tool for manual verification of probe logic.

/DNA/: [list_devices() -> print] + [get_writeback_status() -> print]

- SrcDeps: core.device_management.prober{list_devices, get_writeback_status, is_device_active}, core.os_utils.NotBlockDeviceError
- SysDeps: None

API:
  - run_tests(device_name): Prints formatted probe results for a single device or all active nodes.


### [FILE: test_safety.py] [WIP]
Role: Validation of block device safety guardrails.

/DNA/: [check_device_safety(/dev/root) -> expect(False)] + [check_device_safety(/tmp/file) -> expect(True)]

- SrcDeps: core.os_utils{check_device_safety, run}
- SysDeps: findmnt, os

API:
  - TestDeviceSafety(BaseTestCase): Verifies that active swap and root partitions are never flagged as "safe" for clobbering.


### [FILE: verify_state.py] [WIP]
Role: Diagnostic summary of the system's live ZRAM state.

/DNA/: [run(zramctl) -> run(cat /proc/swaps) -> run(systemctl status)]

- SrcDeps: None
- SysDeps: zramctl, systemctl, subprocess, cat

API:
  - main(): Prints a multi-section dashboard of current ZRAM health and configuration.
