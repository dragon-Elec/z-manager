# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/tests/integration
High-level integration tests for Z-Manager. These tests verify end-to-end orchestration of ZRAM devices, hibernation swapfiles, and configuration persistence across systemd services and bootloaders.

# Rules
!Rule: [Run as Root] - Reason: Integration tests mutate real system state (ZRAM nodes, systemd services, `/etc` files) and require `sudo`.

# Atomic Notes
!Pattern: [Mocked vs. Real System] - Reason: Some tests (e.g., `test_safety.py`) use `BaseTestCase` but interact with real device nodes, while others are standalone scripts that invoke shell commands directly.
!Decision: [Loop Device for WB] - Reason: `test_persistence.py` and `test_modifications.py` use `losetup` to create virtual backing devices for testing writeback functionality without needing physical disks.

# Index
__init__.py: Package marker for test discovery.
test_hibernation_privileged.py: End-to-end audit of hibernation swap lifecycle and bootloader config.
test_hibernation_readonly.py: Non-destructive system capability and state probing checks.
test_modifications.py: Live writeback attachment and device reset orchestration.
test_persistence.py: Validation of INI persistence and systemd-zram-generator auto-restore.
test_queries.py: CLI verification tool for device management probe logic.
test_safety.py: Block device safety guardrails for root/swap protection.
verify_state.py: Diagnostic dashboard for live ZRAM health.

# Audits

### [FILE: test_hibernation_privileged.py] [DONE]
Role: End-to-end audit of hibernation swap lifecycle and bootloader configuration.

/DNA/: [create_swapfile() -> swapon()] + [persist_swap_unit() -> verify /etc/systemd] + [update_grub_resume() -> verify /etc/default/grub.d]

- SrcDeps: core.hibernation.{provisioner, prober, configurator}
- SysDeps: pytest, os, swapon, swapoff, systemctl

API:
  - TestSwapLifecycle: Verifies real swapfile creation, activation, unit persistence, and deletion.
  - TestGrubConfig: Verifies writing of `99-z-manager-resume.cfg` to grub.d.
  - TestSystemDetection: Verifies real bootloader and initramfs discovery without mocks.
!Rule: [Run as Root] - Reason: Requires `swapon` and writes to privileged `/etc` directories.


### [FILE: test_hibernation_readonly.py] [DONE]
Role: Non-destructive system capability and state probing checks.

/DNA/: [check_hibernation_readiness() -> verify SecureBoot/RAM/Swap] + [read_file(/proc/swaps|/sys/power/state)]

- SrcDeps: core.hibernation.prober, core.utils.common.read_file
- SysDeps: pytest, /sys, /proc

API:
  - TestReadinessProbe: Verifies combined readiness status including SecureBoot state.
  - TestSwapDetection: Verifies non-destructive reading of active swaps.
  - TestSystemState: Verifies accessibility of power and kernel lockdown states.


### [FILE: test_modifications.py] [DONE]
Role: End-to-end testing of live writeback attachment and device resets.

/DNA/: [set_writeback(create_if_missing=True) -> verify_status] + [swapon -> set_writeback(force=True) -> verify] + [reset_device() -> verify disksize=0]

- SrcDeps: core.device_management{configurator, provisioner, prober}, core.utils.common{ValidationError, NotBlockDeviceError}
- SysDeps: os, sys, sudo, mkswap, swapon, swapoff

API:
  - run_all_tests(zram_dev, wb_dev): Sequentially executes writeback attachment, force-overrides on active nodes, and block-level resets.


### [FILE: test_persistence.py] [DONE]
Role: Validation of zram-generator.conf persistence and service auto-restore.

/DNA/: [persist_writeback(apply_now=True) -> verify_config_written] + [sysfs_reset_device() -> systemctl restart -> verify_live_restore]

- SrcDeps: core.device_management.configurator{persist_writeback, ensure_writeback_state}, core.device_management.prober.get_writeback_status, core.utils.zram_stats.sysfs_reset_device, core.config.CONFIG_PATH
- SysDeps: configparser, losetup, systemctl, swapoff

API:
  - test_persist_and_recreate(zram_dev, wb_dev): Simulates a service restart to verify that settings are re-applied from `/etc`.


### [FILE: test_queries.py] [DONE]
Role: CLI tool for manual verification of probe logic.

/DNA/: [list_devices() -> print] + [get_writeback_status() -> print] + [is_device_active() -> print]

- SrcDeps: core.device_management.prober{list_devices, get_writeback_status, is_device_active}, core.utils.common.NotBlockDeviceError
- SysDeps: None

API:
  - run_tests(device_name): Prints formatted probe results for a single device or all active nodes.


### [FILE: test_safety.py] [DONE]
Role: Validation of block device safety guardrails.

/DNA/: [findmnt(/) -> check_device_safety(root) -> expect(False)] + [check_device_safety(/tmp/file) -> expect(True)]

- SrcDeps: core.utils.block.check_device_safety, core.utils.common.run
- SysDeps: findmnt, os, blkid

API:
  - TestDeviceSafety(BaseTestCase): Verifies that root partitions and active swap are protected from destructive operations.


### [FILE: verify_state.py] [DONE]
Role: Diagnostic summary of the system's live ZRAM state.

/DNA/: [run(zramctl) -> run(cat /proc/swaps) -> run(systemctl status)]

- SrcDeps: None
- SysDeps: zramctl, systemctl, subprocess, cat

API:
  - main(): Prints a multi-section dashboard of current ZRAM health and configuration.
