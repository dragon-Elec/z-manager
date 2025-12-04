# zman/modules/monitoring.py
"""
Provides real-time monitoring functions (generators) for system statistics.
These are intended to be used by a UI for live-updating dashboards.
"""
from __future__ import annotations

import logging
import time
from typing import Iterator, NamedTuple

import psutil

from core.zdevice_ctl import get_writeback_status

_LOGGER = logging.getLogger(__name__)

def watch_device_usage(device_name: str, interval: float = 1.0) -> Iterator[int]:
    """
    Generator that yields the current uncompressed data size (in bytes) of a ZRAM device.

    This is useful for powering real-time UI elements like graphs. It will run
    indefinitely until the device is no longer accessible, at which point the
    iterator will stop.

    Args:
        device_name: The name of the ZRAM device (e.g., "zram0").
        interval: The time in seconds to wait between yielding updates.

    Yields:
        The size of the original data stored in ZRAM, in bytes.
    """
    _LOGGER.info(f"Starting usage watch for '{device_name}' with {interval}s interval.")
    while True:
        try:
            status = get_writeback_status(device_name)

            # The sysfs file might not exist if the device is reset
            if status and status.orig_data_size is not None:
                # The value from sysfs is a string representing bytes. Convert to int.
                usage_bytes = int(status.orig_data_size)
                yield usage_bytes
            else:
                # If status is None or size is not available, the device might be gone.
                _LOGGER.warning(f"Stopping usage watch for '{device_name}': device or stats are no longer available.")
                break

            time.sleep(interval)
        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Could not parse usage for '{device_name}': {e}. Stopping watch.")
            break
        except Exception as e:
            _LOGGER.error(f"Unexpected error during usage watch for '{device_name}': {e}. Stopping watch.")
            break


class SystemStats(NamedTuple):
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int


def watch_system_stats(interval: float = 1.0) -> Iterator[SystemStats]:
    """
    Generator that yields real-time system statistics using psutil.
    Yields a SystemStats tuple containing CPU and Memory usage.
    """
    _LOGGER.info(f"Starting system stats watch with {interval}s interval.")
    while True:
        try:
            # cpu_percent(interval=None) is non-blocking if called repeatedly.
            # However, the first call might return 0.0.
            # We rely on the loop interval for timing.
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            
            yield SystemStats(
                cpu_percent=cpu,
                memory_percent=mem.percent,
                memory_used=mem.used,
                memory_total=mem.total
            )
            
            time.sleep(interval)
        except Exception as e:
            _LOGGER.error(f"Error in system stats watch: {e}")
            time.sleep(interval) # Wait before retrying to avoid busy loop on error
