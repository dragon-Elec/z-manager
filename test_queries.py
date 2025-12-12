#!/usr/bin/env python3

# test_queries.py

import sys
# Corrected version
from core.zdevice_ctl import (
    list_devices,
    get_writeback_status,
    is_device_active,
    NotBlockDeviceError
)

def run_tests(device_name="zram0"):
    """Run all query tests and print the results."""
    print("--- Running Query Tests ---")

    # 1. Test list_devices()
    print("\n[1] Testing list_devices():")
    try:
        devices = list_devices()
        if not devices:
            print("    Result: No devices found. (OK)")
        else:
            print(f"    Result: Found {len(devices)} device(s).")
            for dev in devices:
                print(f"      - {dev}")
    except Exception as e:
        print(f"    ERROR: {e}")

    # 2. Test get_writeback_status()
    print(f"\n[2] Testing get_writeback_status('{device_name}'):")
    try:
        status = get_writeback_status(device_name)
        print(f"    Result: {status}")
    except NotBlockDeviceError:
        print(f"    Result: Device {device_name} does not exist. (OK)")
    except Exception as e:
        print(f"    ERROR: {e}")

    # 3. Test is_device_active()
    print(f"\n[3] Testing is_device_active('{device_name}'):")
    try:
        active = is_device_active(device_name)
        print(f"    Result: {active}")
    except Exception as e:
        print(f"    ERROR: {e}")

    print("\n--- Tests Complete ---")

if __name__ == "__main__":
    # Allows specifying a different device, e.g., python3 test_queries.py zram1
    target_device = sys.argv[1] if len(sys.argv) > 1 else "zram0"
    run_tests(target_device)
