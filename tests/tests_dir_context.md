# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-man/z-manager/tests
Primary test suite for Z-Manager. Provides infrastructure for isolated unit testing and full-cycle integration testing of ZRAM lifecycle and system orchestration.

# Rules
!Rule: [Inherit BaseTestCase] - Reason: Ensures consistent access to system-level mocking utilities and prevents accidental real system mutation.

# Atomic Notes
!Pattern: [Mocked System I/O] - Reason: `BaseTestCase.mock_system_calls` centralizes logic for patching `core.utils.common` to prevent environment leakage and side effects.
!Decision: [Direct Sysfs Cleanup] - Reason: `cleanup_zram.sh` resets zram devices via sysfs to ensure tests start from a clean state without needing `zramctl`.

# Index
__init__.py: Package marker for test discovery.
integration: Large-scale tests verifying cross-module coordination (see integration_dir_context.md).
unit: Granular tests for individual core and device_management modules (see unit_dir_context.md).

# Audits

### [FILE: test_base.py] [WIP]
Role: Testing infrastructure and common mocking primitives.

/DNA/: [BaseTestCase.mock_system_calls() -> patch(core.utils.common.{read_file, run}) -> addCleanup()]

- SrcDeps: core.utils.common{read_file, run}, core.utils.units.parse_size_to_bytes, core.device_management.prober.is_device_active
- SysDeps: unittest, unittest.mock{patch, MagicMock, mock_open}

API:
  - BaseTestCase(unittest.TestCase):
    - mock_system_calls(read_data, run_result): Mocks common system interactions.
    - assertValidSize(size_str): Verifies string resolves to bytes > 0.
    - assertAlgorithm(device, expected): Stub for cross-checking device compression algorithm.


### [FILE: cleanup_zram.sh] [WIP]
Role: Reset script for ZRAM device nodes.

/DNA/: [loop /sys/block/zram* -> swapoff -> echo 1 > reset]

- SrcDeps: None
- SysDeps: bash, sudo, swapoff, tee

API:
  - None (Shell Script)
