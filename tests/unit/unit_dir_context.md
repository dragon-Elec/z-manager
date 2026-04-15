# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/tests/unit
Isolated unit tests for Z-Manager core and business logic. Each test file targets a specific module, using `BaseTestCase` to mock system interaction and verify internal state transitions without side effects.

# Rules
!Rule: [Inherit BaseTestCase] - Reason: Centralizes mocking logic and prevents accidental mutation of the host system during test execution.

# Atomic Notes
!Pattern: [One-to-One Mapping] - Reason: Test filenames mirror the core module they validate (e.g., `test_runtime.py` -> `runtime.py`).
!Pattern: [Mocked Sysfs Reads] - Reason: Parser tests heavily use `patch` on `read_file` to simulate various sysfs states and edge cases (e.g., malformed PSI data, missing devices).
!Pattern: [ConfigObj Preservation] - Reason: Preservation tests verify that `ConfigObj` maintains user comments and global sections during INI updates.

# Index
__init__.py: Package marker for test discovery.
test_boot_config_modern.py: Validation of sysctl persistence and value application.
test_config_provenance.py: Validation of systemd-style config merging and origin tracking.
test_config_safety.py: Validation of atomic and idempotent file operations.
test_config_systemd_integration.py: Integration test between parser and systemd-analyze binary.
test_config_validation.py: Security and integrity checks for configuration inputs.
test_global_config.py: Validation of [zram-generator] section management.
test_hibernate_systemd.py: Specialized validation of systemd swap units.
test_hibernation_configurator.py: Validation of bootloader discovery for hibernation.
test_hibernation_prober.py: Validation of system capability and swap property discovery.
test_hibernation_provisioner.py: Validation of hibernation swapfile lifecycle and units.
test_journal.py: Validation of systemd journal log extraction.
test_monitoring_psutil.py: Validation of async-style stat generator.
test_parser_robustness.py: Resilience testing for sysfs property parsing.
test_preservation.py: Regression tests for INI comment stripping.
test_profiles.py: Validation of JSON profile lifecycle.
test_psi.py: Validation of Pressure Stall Information (PSI) parsing.
test_runtime.py: Validation of runtime system tuning (CPU/IO/VFS).
test_size_parser.py: Validation of human-readable size parsing.
test_zdevice_ctl.py: Validation of device management prober and types.

# Audits

### [FILE: test_runtime.py] [DONE]
Role: Validation of runtime system tuning (CPU/IO/VFS).

/DNA/: [runtime.set_cpu_governor() -> mock_glob() -> mock_available() -> mock_write() -> assert result]

- SrcDeps: modules.runtime
- SysDeps: pathlib.Path, unittest.mock.patch

API:
  - TestCpuGovernor(BaseTestCase): Verify available detection and sysfs writing.
  - TestIoScheduler(BaseTestCase): Verify bracket parsing in `scheduler` sysfs file.
  - TestVfsCachePressure(BaseTestCase): Verify boundary checks (0-500) and default fallback.


### [FILE: test_hibernation_configurator.py] [DONE]
Role: Validation of bootloader discovery and hibernation parameter injection.

/DNA/: [detect_bootloader() -> which(update-grub|bootctl) -> ok] + [update_grub_resume() -> pkexec_write(GRUB_CMDLINE_LINUX_DEFAULT)]

- SrcDeps: core.utils.bootloader{detect_bootloader, detect_initramfs_system}, core.utils.kernel_cmdline.is_kernel_param_active, core.hibernation.configurator{update_grub_resume, configure_initramfs_resume}
- SysDeps: unittest.mock.{patch, MagicMock}, shutil, os

API:
  - TestSystemDetection(BaseTestCase): Verifies detection of grub, systemd-boot, initramfs-tools, dracut.
  - TestResumeConfig(BaseTestCase): Verifies success/failure of GRUB and initramfs resume configuration.
  - TestKernelParam(BaseTestCase): Verifies `resume=` and `resume_offset=` detection in `/proc/cmdline`.


### [FILE: test_hibernation_prober.py] [DONE]
Role: Validation of system capability probing and swap property discovery.

/DNA/: [check_hibernation_readiness() -> busctl(CanHibernate) -> fallback(/sys/power/state)] + [get_resume_offset() -> filefrag/btrfs-inspect -> parse physical offset]

- SrcDeps: core.hibernation.prober, core.utils.swap.detect_resume_swap
- SysDeps: unittest.mock.{patch, MagicMock}

API:
  - TestProber(BaseTestCase):
    - check_hibernation_readiness(): Verifies busctl yes/no/na logic.
    - get_resume_offset(): Verifies btrfs vs ext4 offset calculation.
    - get_partition_uuid(): Verifies UUID resolution from block device or file.
    - detect_resume_swap(): Verifies selection of non-zram swap devices.
    - get_memory_info(): Verifies RAM/Swap total parsing from `/proc/meminfo`.


### [FILE: test_hibernation_provisioner.py] [DONE]
Role: Validation of hibernation swapfile lifecycle and systemd unit generation.

/DNA/: [create_swapfile() -> fallocate/truncate -> mkswap -> swapon] + [persist_swap_unit() -> write .swap -> systemctl enable]

- SrcDeps: core.hibernation.provisioner
- SysDeps: unittest.mock.{patch, MagicMock, PropertyMock}, os, pathlib.Path

API:
  - TestProvisioner(BaseTestCase):
    - create_swapfile(): Verifies FS-specific creation commands (ext4 vs btrfs).
    - generate_swap_unit(): Verifies systemd unit template content.
    - escape_unit_name(): Verifies escaping logic (systemd-escape fallback).
    - persist_swap_unit(): Verifies path, reload, and enable calls.
    - delete_swap(): Verifies swapoff and file/unit removal.


### [FILE: test_hibernate_systemd.py] [DONE]
Role: Specialized validation of systemd swap units.

/DNA/: [generate_swap_unit() -> assert text] + [persist_swap_unit() -> mock calls]

- SrcDeps: core.hibernation.provisioner
- SysDeps: unittest.mock.{patch, MagicMock}

API:
  - TestHibernateSystemd(BaseTestCase):
    - test_generate_swap_unit_content(): Verifies unit sections.
    - test_escape_unit_name(): Verifies unit naming.
    - test_persist_swap_unit_calls(): Verifies pkexec interactions.


### [FILE: test_boot_config_modern.py] [DONE]
Role: Validation of sysctl persistence and value application.

/DNA/: [apply_sysctl_values(settings) -> read_file() -> diff check -> if(changes) -> pkexec_write() -> pkexec_sysctl_system() -> return result]

- SrcDeps: core.boot_config
- SysDeps: pathlib, unittest.mock.patch, core.utils.{io, privilege}

API:
  - TestSysctlTuning(BaseTestCase):
    - test_apply_sysctl_values_success(): Verify atomic write and system reload.
    - test_apply_sysctl_values_permission_denied(): Verify graceful handling of pkexec failure.
    - test_apply_sysctl_values_no_change(): Verify idempotent skip if content matches.


### [FILE: test_config_provenance.py] [DONE]
Role: Validation of systemd-style configuration merging and origin tracking.

/DNA/: [_parse_systemd_cat_config(mock_output) -> parse files/sections -> return EffectiveConfig(config, provenance)]

- SrcDeps: core.config{_parse_systemd_cat_config, EffectiveConfig}
- SysDeps: tests.test_base

API:
  - TestConfigProvenance(BaseTestCase):
    - test_deep_merge_parsing(): Verifies override/inherits/drop-in priority (Vendor -> Drop-in -> Admin).
    - test_empty_input(): Verifies robust handling of empty systemd-analyze output.


### [FILE: test_config_systemd_integration.py] [DONE]
Role: Integration test verifying interaction between the parser and the systemd-analyze binary.

/DNA/: [load_effective_config_state(root) -> run(systemd-analyze --root=... cat-config ...) -> parse output]

- SrcDeps: core.config.load_effective_config_state
- SysDeps: os, shutil, tempfile, pathlib.Path, tests.test_base

API:
  - TestConfigSystemdIntegration(BaseTestCase):
    - test_real_systemd_analyze_merging(): Seeds mock /etc and /usr/lib hierarchy and verifies "Hierarchy of Truth".


### [FILE: test_config_validation.py] [DONE]
Role: Security and integrity checks for configuration inputs.

/DNA/: [validate_updates(data) -> check injection patterns -> match regex -> return error/None]

- SrcDeps: core.config_writer{validate_updates, update_zram_config}
- SysDeps: None (Logic-only)

API:
  - TestConfigValidation(BaseTestCase):
    - test_size_validation(): Verify RAM formulas and basic injection block.
    - test_injection_hardening(): CRITICAL verify protection against newline/section/key injection.
    - test_algo_validation(): Verify algorithm strings and separator safety.
    - test_swap_priority_validation(): Verify integer-only constraints for priority.
    - test_global_section_protection(): Ensure `[zram-generator]` section is reserved.


### [FILE: test_profiles.py] [DONE]
Role: Validation of JSON profile lifecycle.

/DNA/: [profiles.get_all_profiles() -> temp_dir() -> merge builtins + user files] + [save_profile() -> json.dump() -> exists()]

- SrcDeps: modules.profiles
- SysDeps: os, json, tempfile, shutil, pathlib.Path

API:
  - TestProfiles(BaseTestCase):
    - test_get_all_profiles_includes_user_profiles(): Verify merging of builtins and disk files.
    - test_load_profile_user_profile(): Verify specific file loading by name.
    - test_save_profile_creates_file(): Verify disk writing and builtin protection.
    - test_delete_profile_removes_file(): Verify disk cleanup and builtin protection.
    - test_load_malformed_json(): Verify resilience against corrupted JSON files.


### [FILE: test_zdevice_ctl.py] [DONE]
Role: Validation of device management prober and types.

/DNA/: [prober.list_devices() -> parse_zramctl_table() -> wrap DeviceInfo] + [get_writeback_status() -> read sysfs -> wrap WritebackStatus]

- SrcDeps: core.device_management{prober, types}
- SysDeps: unittest.mock.patch

API:
  - TestListDevices(BaseTestCase): Verify conversion of raw sysfs dicts to `DeviceInfo` dataclasses.
  - TestGetWritebackStatus(BaseTestCase): Verify backing device detection and stat parsing.
  - Dataclass Tests: Verifies schema and defaults for `DeviceInfo`, `WritebackStatus`, `UnitResult`, `WritebackResult`, `PersistResult`.


### [FILE: test_config_safety.py] [DONE]
Role: Validation of atomic and idempotent file operations.

/DNA/: [atomic_write_to_file() -> if(content_match) -> skip_write -> else -> tempfile+move]

- SrcDeps: core.utils.io.atomic_write_to_file
- SysDeps: os, shutil, tempfile, time

API:
  - TestConfigSafety(BaseTestCase): Verifies mtime stability on identical writes and backup `.bak` creation.


### [FILE: test_size_parser.py] [DONE]
Role: Validation of human-readable size parsing.

/DNA/: [units.parse_size_to_bytes() -> regex -> math unit multiplier]

- SrcDeps: core.utils.units
- SysDeps: None

API:
  - TestSizeParser(BaseTestCase): Verifies support for K, M, G, GiB units and decimals.


### [FILE: test_journal.py] [DONE]
Role: Validation of systemd journal log extraction and fallbacks.

/DNA/: [journal.list_zram_logs() -> if(import systemd) -> use C-API -> else -> run(journalctl)]

- SrcDeps: modules.journal
- SysDeps: datetime, unittest.mock.patch

API:
  - TestListZramLogs(BaseTestCase): Verify fallback to CLI when `python3-systemd` is missing.


### [FILE: test_psi.py] [DONE]
Role: Validation of Pressure Stall Information (PSI) parsing.

/DNA/: [psi.get_psi() -> read_file(/proc/pressure/...) -> parse key=avg]

- SrcDeps: modules.psi
- SysDeps: unittest.mock.patch

API:
  - TestPsi(BaseTestCase): Verify robust handling of malformed or missing PSI files.


### [FILE: test_monitoring_psutil.py] [DONE]
Role: Validation of async-style stat generator.

/DNA/: [monitoring.watch_system_stats() -> yield SystemStats(cpu, mem)]

- SrcDeps: modules.monitoring
- SysDeps: psutil (via modules.monitoring)

API:
  - TestMonitoringPsutil(BaseTestCase): Verify sampling loop and datatype consistency.


### [FILE: test_preservation.py] [DONE]
Role: Regression tests for INI comment stripping.

/DNA/: [update_zram_config() -> merge updates -> verify diff contains comments]

- SrcDeps: core.config_writer.update_zram_config, core.config.get_active_config_path
- SysDeps: os, tempfile

API:
  - TestConfigPreservation(BaseTestCase): Ensures user comments in existing config are NOT deleted by `ConfigObj`.


### [FILE: test_parser_robustness.py] [DONE]
Role: Resilience testing for sysfs property parsing.

/DNA/: [zram_stats.parse_zramctl_table() -> loop sysfs -> if(IOError) -> skip -> return list]

- SrcDeps: core.utils.zram_stats
- SysDeps: unittest.mock.patch

API:
  - TestSysfsParser(BaseTestCase): Verifies graceful failure when device disappears mid-probe.


### [FILE: test_global_config.py] [DONE]
Role: Validation of [zram-generator] section management.

/DNA/: [read_global_config() -> filter sections -> returns dict] + [update_global_config() -> render ConfigObj -> verify zram-generator block]

- SrcDeps: core.config.read_global_config, core.config_writer.update_global_config
- SysDeps: configobj

API:
  - TestGlobalConfig(BaseTestCase): Verify separation between per-device and global settings.
