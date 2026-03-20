# z-manager/core/zdevice_ctl.py
"""
Shim for backward compatibility.
This file re-exports symbols from the functionally-split modules in core/device_management/.
New code should ideally import directly from core.device_management.[prober|provisioner|configurator|types].
"""

from .os_utils import (
    is_block_device,
    parse_zramctl_table,
    NotBlockDeviceError,
    ValidationError,
    SystemCommandError
)

from .device_management.types import (
    DeviceInfo,
    WritebackStatus,
    UnitResult,
    WritebackResult,
    PersistResult,
    Action,
    OrchestrationResult
)

from .device_management.prober import (
    list_devices,
    get_writeback_status,
    is_device_active,
    read_params_best_effort
)

from .device_management.provisioner import (
    ensure_device_exists,
    reconfigure_device_sysfs,
    reset_device
)

from .device_management.configurator import (
    apply_device_config,
    apply_global_config,
    remove_device_config,
    set_writeback,
    clear_writeback,
    restart_unit_for_device,
    restart_device_unit,
    persist_writeback,
    ensure_writeback_state
)

# Compatibility aliases for any legacy calls that might expect internal names
_ensure_device_exists = ensure_device_exists
_reconfigure_device_sysfs = reconfigure_device_sysfs
_device_active = is_device_active
_get_sysfs = _get_sysfs
_read_params_best_effort = read_params_best_effort
