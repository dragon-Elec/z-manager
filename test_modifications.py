#!/usr/bin/env python3

# test_modifications.py

import sys
import os
from core.zdevice_ctl import (
    set_writeback,
    clear_writeback,
    reset_device,
    get_writeback_status,
    is_device_active,
    ValidationError,
    NotBlockDeviceError
)

def run_all_tests(zram_dev, wb_dev):
    """Run all modification tests sequentially."""
    print(f"--- Running Modification Tests on '{zram_dev}' with writeback target '{wb_dev}' ---")

    # 1. Test set_writeback on a new/inactive device
    print("\n[1] Testing set_writeback (inactive device)...")
    try:
        # The function should create the device if it's missing
        result = set_writeback(zram_dev, wb_dev, create_if_missing=True)
        print(f"    Result: {result}")
        # Verification step
        status = get_writeback_status(zram_dev)
        print(f"    Verification: backing_dev is '{status.backing_dev}'")
        assert status.backing_dev == wb_dev
    except Exception as e:
        print(f"    ERROR: {e}")

    # 2. Test clear_writeback on the same device
    print("\n[2] Testing clear_writeback (inactive device)...")
    try:
        result = clear_writeback(zram_dev)
        print(f"    Result: {result}")
        # Verification step
        status = get_writeback_status(zram_dev)
        print(f"    Verification: backing_dev is '{status.backing_dev}'")
        assert status.backing_dev == 'none'
    except Exception as e:
        print(f"    ERROR: {e}")

    # 3. Test force=True on an ACTIVE device
    print("\n[3] Testing 'force' parameter on an active device...")
    try:
        # First, make the device active
        print("    Action: Activating device with mkswap/swapon...")
        os.system(f"sudo mkswap /dev/{zram_dev} > /dev/null")
        os.system(f"sudo swapon /dev/{zram_dev}")
        print(f"    Verification: is_device_active is '{is_device_active(zram_dev)}'")

        # Attempt to set writeback WITHOUT force (should fail)
        print("    Action: Attempting set_writeback without force (expecting error)...")
        try:
            set_writeback(zram_dev, wb_dev)
        except ValidationError:
            print("    Result: SUCCESS (Caught expected ValidationError)")

        # Attempt to set writeback WITH force (should succeed)
        print("    Action: Attempting set_writeback with force=True...")
        result = set_writeback(zram_dev, wb_dev, force=True)
        print(f"    Result: {result}")
        status = get_writeback_status(zram_dev)
        print(f"    Verification: backing_dev is '{status.backing_dev}'")
        assert status.backing_dev == wb_dev

        # Clean up swap
        os.system(f"sudo swapoff /dev/{zram_dev} > /dev/null")

    except Exception as e:
        print(f"    ERROR: {e}")

    # 4. Test reset_device
    print("\n[4] Testing reset_device...")
    try:
        # First, ensure the device exists and has a non-zero size.
        # We can use set_writeback to get it into a known state.
        print("    Action: Configuring device to have a size...")
        set_writeback(zram_dev, wb_dev, create_if_missing=True, new_size="128M")

        # Now, reset it using our sysfs-based function
        print("    Action: Calling reset_device()...")
        result = reset_device(zram_dev)
        print(f"    Result: {result}")
        assert result.success

        # Verification: The device should still exist, but its disksize should be 0.
        if os.path.exists(f"/dev/{zram_dev}"):
            status_output = os.popen(f"cat /sys/block/{zram_dev}/disksize").read().strip()
            if status_output == "0":
                print(f"    Verification: SUCCESS - Device exists and disksize is '{status_output}'.")
            else:
                print(f"    Verification: FAILED - Device disksize is '{status_output}', expected '0'.")
                assert status_output == "0"
        else:
            print(f"    Verification: FAILED - Device /dev/{zram_dev} was unexpectedly removed.")
            assert os.path.exists(f"/dev/{zram_dev}")

    except Exception as e:
        print(f"    ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: sudo python3 {sys.argv[0]} <zram_device_name> <writeback_device_path>")
        print(f"Example: sudo python3 {sys.argv[0]} zram0 /dev/loop14")
        print()
        print("Before running, create a loop device for writeback testing:")
        print("  truncate -s 100M /tmp/test_writeback.img")
        print("  sudo losetup /dev/loop14 /tmp/test_writeback.img")
        sys.exit(1)

    zram_device = sys.argv[1]
    writeback_device = sys.argv[2]
    run_all_tests(zram_device, writeback_device)

