# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/tests/unit
Isolated unit tests for Z-Manager core and business logic. Each test file targets a specific module, using `BaseTestCase` to mock system interaction and verify internal state transitions without side effects.

# Rules
!Rule: [Inherit BaseTestCase] - Reason: Centralizes mocking logic and prevents accidental mutation of the host system during test execution.

# Atomic Notes
!Pattern: [One-to-One Mapping] - Reason: Test filenames mirror the core module they validate (e.g., `test_runtime.py` -> `runtime.py`).
!Pattern: [Mocked Sysfs Reads] - Reason: Parser tests heavily use `patch` on `read_file` to simulate various sysfs states and edge cases (e.g., malformed PSI data, missing devices).
!Pattern: [ConfigObj Preservation] - Reason: Preservation tests verify that `ConfigObj` maintains user comments and global sections during INI updates.

# Index
__init__.py: Package marker for test discovery.

# Audits

### [FILE: test_runtime.py] [WIP]
Role: Validation of runtime system tuning (CPU/IO/VFS).

/DNA/: [runtime.set_cpu_governor() -> mock_glob() -> mock_available() -> mock_write() -> assert result]

- SrcDeps: modules.runtime
- SysDeps: pathlib.Path, unittest.mock.patch

API:
  - TestCpuGovernor(BaseTestCase): Verify available detection and sysfs writing.
  - TestIoScheduler(BaseTestCase): Verify bracket parsing in `scheduler` sysfs file.
  - TestVfsCachePressure(BaseTestCase): Verify boundary checks (0-500) and default fallback.


### [FILE: test_hibernate_ctl.py] [WIP]
Role: Validation of hibernation swap orchestration.

/DNA/: [hibernate_ctl.create_swapfile() -> mock_fs_type() -> if(btrfs) -> (truncate+chattr) -> else -> fallocate]

- SrcDeps: core.hibernate_ctl, core.utils.common.SystemCommandError
- SysDeps: os, sys, unittest.mock.patch

API:
  - TestHibernateCtl(BaseTestCase):
    - test_check_readiness_basic(): Verify Secure Boot detection logic.
    - test_create_swapfile_ext4/btrfs(): Verify command sequence differences per FS.
    - test_update_fstab(): Verify `nofail` and `pri` presence in generated entries.


### [FILE: test_boot_config_modern.py] [WIP]
Role: Validation of bootloader detection and sysctl persistence.

/DNA/: [boot_config.detect_bootloader() -> mock_which() -> mock_isdir() -> return string]

- SrcDeps: core.boot_config
- SysDeps: os, shutil, pathlib, unittest.mock.patch

API:
  - TestSystemDetection(BaseTestCase): Verify grub vs systemd-boot vs dracut detection.
  - TestSysctlTuning(BaseTestCase): Verify `atomic_write_to_file` integration for sysctl profiles.


### [FILE: test_config_validation.py] [WIP]
Role: Security and integrity checks for configuration inputs.

/DNA/: [validate_updates(data) -> check injection patterns -> return error/None]

- SrcDeps: core.config_writer{validate_updates, update_zram_config}
- SysDeps: None (Logic-only)

API:
  - TestConfigValidation(BaseTestCase):
    - test_size_validation(): Verify RAM formulas and injection block.
    - test_global_section_protection(): Ensure `[zram-generator]` section is reserved.


### [FILE: test_profiles.py] [WIP]
Role: Validation of JSON profile lifecycle.

/DNA/: [profiles.get_all_profiles() -> temp_dir() -> merge builtins + user files]

- SrcDeps: modules.profiles
- SysDeps: os, json, tempfile, shutil, pathlib.Path

API:
  - TestProfiles(BaseTestCase): Verify CRUD operations and built-in protection.


### [FILE: test_zdevice_ctl.py] [WIP]
Role: Validation of device management prober and types.

/DNA/: [prober.list_devices() -> mock_parse_zramctl_table() -> yield DeviceInfo]

- SrcDeps: core.device_management{prober, types}
- SysDeps: unittest.mock.patch

API:
  - TestListDevices(BaseTestCase): Verify conversion of raw sysfs dicts to `DeviceInfo` dataclasses.
  - TestGetWritebackStatus(BaseTestCase): Verify backing device detection and stat parsing.


### [FILE: test_config_safety.py] [WIP]
Role: Validation of atomic and idempotent file operations.

/DNA/: [atomic_write_to_file() -> if(content_match) -> skip_write -> else -> tempfile+move]

- SrcDeps: core.utils.io.atomic_write_to_file
- SysDeps: os, shutil, tempfile, time

API:
  - TestConfigSafety(BaseTestCase): Verifies mtime stability on identical writes and backup `.bak` creation.


### [FILE: test_size_parser.py] [WIP]
Role: Validation of human-readable size parsing.

/DNA/: [units.parse_size_to_bytes() -> regex -> math unit multiplier]

- SrcDeps: core.utils.units
- SysDeps: None

API:
  - TestSizeParser(BaseTestCase): Verifies support for K, M, G, GiB units and decimals.


### [FILE: test_journal.py] [WIP]
Role: Validation of systemd journal log extraction and fallbacks.

/DNA/: [journal.list_zram_logs() -> if(import systemd) -> use C-API -> else -> run(journalctl)]

- SrcDeps: modules.journal
- SysDeps: datetime, unittest.mock.patch

API:
  - TestListZramLogs(BaseTestCase): Verify fallback to CLI when `python3-systemd` is missing.


### [FILE: test_psi.py] [WIP]
Role: Validation of Pressure Stall Information (PSI) parsing.

/DNA/: [psi.get_psi() -> read_file(/proc/pressure/...) -> parse key=avg]

- SrcDeps: modules.psi
- SysDeps: unittest.mock.patch

API:
  - TestPsi(BaseTestCase): Verify robust handling of malformed or missing PSI files.


### [FILE: test_monitoring_psutil.py] [WIP]
Role: Validation of async-style stat generator.

/DNA/: [monitoring.watch_system_stats() -> yield SystemStats(cpu, mem)]

- SrcDeps: modules.monitoring
- SysDeps: psutil (via modules.monitoring)

API:
  - TestMonitoringPsutil(BaseTestCase): Verify sampling loop and datatype consistency.


### [FILE: test_preservation.py] [WIP]
Role: Regression tests for INI comment stripping.

/DNA/: [update_zram_config() -> merge updates -> verify diff contains comments]

- SrcDeps: core.config_writer.update_zram_config, core.config.get_active_config_path
- SysDeps: os, tempfile

API:
  - TestConfigPreservation(BaseTestCase): Ensures user comments in existing config are NOT deleted by `ConfigObj`.


### [FILE: test_parser_robustness.py] [WIP]
Role: Resilience testing for sysfs property parsing.

/DNA/: [zram_stats.parse_zramctl_table() -> loop sysfs -> if(IOError) -> skip -> return list]

- SrcDeps: core.utils.zram_stats
- SysDeps: unittest.mock.patch

API:
  - TestSysfsParser(BaseTestCase): Verifies graceful failure when device disappears mid-probe.


### [FILE: test_global_config.py] [WIP]
Role: Validation of [zram-generator] section management.

/DNA/: [read_global_config() -> filter sections -> return zram-generator dict]

- SrcDeps: core.config.read_global_config, core.config_writer.update_global_config
- SysDeps: configobj

API:
  - TestGlobalConfig(BaseTestCase): Verify separation betweeen per-device and global settings.
