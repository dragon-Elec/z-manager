# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/tests
Primary test suite for Z-Manager. Provides infrastructure for isolated unit testing and full-cycle integration testing of ZRAM lifecycle and system orchestration.

# Rules
!Rule: [Inherit BaseTestCase] - Reason: Ensures consistent access to system-level mocking utilities and prevents accidental real system mutation.

# Atomic Notes
!Pattern: [Mocked System I/O] - Reason: `BaseTestCase.mock_system_calls` centralizes logic for patching `core.utils.common` to prevent environment leakage and side effects.
!Decision: [Direct Sysfs Cleanup] - Reason: `cleanup_zram.sh` resets zram devices via sysfs to ensure tests start from a clean state without needing `zramctl`.

# Index
__init__.py: Package marker for test discovery.
conftest.py: Pytest configuration, custom markers, and shared fixtures.
integration: Large-scale tests verifying cross-module coordination (see integration_dir_context.md).
test_base.py: Core testing infrastructure and mocking primitives.
unit: Granular tests for individual core and device_management modules (see unit_dir_context.md).

# Audits

### [FILE: conftest.py] [DONE]
Role: Pytest configuration and shared fixtures for privileged and integration tests.

/DNA/: [pytest_configure() -> add_markers(privileged, integration) -> pytest_addoption(--privileged) -> pytest_collection_modifyitems() -> if(!--privileged) -> skip(privileged)]

- SrcDeps: os, pytest
- SysDeps: pytest

API:
  - pytest_configure(config): Registers custom markers.
  - pytest_addoption(parser): Adds `--privileged` command-line flag.
  - pytest_collection_modifyitems(config, items): Skips privileged tests by default.
  - requires_root(): Fixture to skip if not root.
  - is_root(): Fixture returning root status.
  - tmp_swap_path(tmp_path): Fixture providing temp swapfile path.


### [FILE: test_base.py] [DONE]
Role: Testing infrastructure and common mocking primitives.

/DNA/: [BaseTestCase.mock_system_calls() -> patch(core.utils.common.{read_file, run}) -> addCleanup()]

- SrcDeps: core.utils.common{read_file, run}, core.utils.units.parse_size_to_bytes, core.device_management.prober.is_device_active
- SysDeps: unittest, unittest.mock{patch, MagicMock, mock_open}

API:
  - BaseTestCase(unittest.TestCase):
    - mock_system_calls(read_data, run_result): Mocks common system interactions.
    - assertDeviceActive(device_name): Verifies zram device is active/swapon.
    - assertValidSize(size_str): Verifies string resolves to bytes > 0.
    - assertAlgorithm(device, expected): Stub for cross-checking device compression algorithm.


### [FILE: cleanup_zram.sh] [DONE]
Role: Reset script for ZRAM device nodes using sysfs.

/DNA/: [loop /sys/block/zram* -> sudo swapoff -> echo 1 | sudo tee reset]

- SrcDeps: None
- SysDeps: bash, sudo, swapoff, tee

API:
  - None (Shell Script)
