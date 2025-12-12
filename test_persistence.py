

#!/usr/bin/env python3

# test_persistence.py

import sys
import os
import time
import configparser
import traceback
from core.zdevice_ctl import (
    persist_writeback,
    ensure_writeback_state,
    get_writeback_status,
    NotBlockDeviceError
)
from core.config import CONFIG_PATH
from core.os_utils import sysfs_reset_device

def cleanup_system(zram_dev, wb_dev):
    """Ensure a clean state before and after tests."""
    print("--- Cleaning up system ---")
    # Remove zram device
    os.system(f"sudo swapoff /dev/{zram_dev} > /dev/null 2>&1")
    try:
        sysfs_reset_device(f"/dev/{zram_dev}")
    except Exception:
        pass  # Ignore errors during cleanup
    # Remove loop device
    os.system(f"sudo losetup -d {wb_dev} > /dev/null 2>&1")
    # Remove config file
    if os.path.exists(CONFIG_PATH):
        os.system(f"sudo rm {CONFIG_PATH}")
    print("--- Cleanup complete ---")

def setup_system(wb_dev):
    """Prepare system for testing."""
    print("--- Setting up system ---")
    os.system(f"truncate -s 100M /tmp/wb_test_file.img")
    os.system(f"sudo losetup {wb_dev} /tmp/wb_test_file.img")
    print("--- Setup complete ---")

def test_persist_and_recreate(zram_dev, wb_dev):
    """
    Tests if a persisted setting is correctly applied after
    the device is destroyed and recreated by systemd.
    """
    print("\n[1] Testing persist_writeback and systemd recreation...")
    try:
        # 1. Persist the setting and apply it now
        print(f"    Action: Persisting writeback '{wb_dev}' for '{zram_dev}'")
        result = persist_writeback(zram_dev, wb_dev, apply_now=True)
        print(f"    Result: {result.message}")
        assert result.success and result.applied

        # 2. Verify the config file was written correctly
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH)
        assert cfg.get(zram_dev, "writeback-device") == wb_dev
        print("    Verification: Config file is correct.")

        # 3. Verify the live device is configured correctly
        live_status = get_writeback_status(zram_dev)
        assert live_status.backing_dev == wb_dev
        print("    Verification: Live device is correct.")

        # 4. SIMULATE REBOOT: Destroy the device and restart the service
        print("    Action: Simulating reboot (resetting device, restarting service)...")
        sysfs_reset_device(f"/dev/{zram_dev}")
        os.system(f"sudo systemctl restart systemd-zram-setup@{zram_dev}.service")

        time.sleep(1)

        # 5. Verify the "post-reboot" state
        recreated_status = get_writeback_status(zram_dev)
        assert recreated_status.backing_dev == wb_dev
        print("    Verification: SUCCESS - Device recreated with persistent settings.")

    except Exception as e:
        print(f"    ERROR: An exception occurred: {e}")
        traceback.print_exc()

def run_all_tests(zram_dev, wb_dev):
    """Run all persistence tests."""
    try:
        cleanup_system(zram_dev, wb_dev)
        setup_system(wb_dev)
        test_persist_and_recreate(zram_dev, wb_dev)
    finally:
        cleanup_system(zram_dev, wb_dev)
        os.system("rm -f /tmp/wb_test_file.img")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: sudo python3 {sys.argv[0]} <zram_device_name> <writeback_device_path>")
        print(f"Example: sudo python3 {sys.argv[0]} zram0 /dev/loop14")
        sys.exit(1)

    zram_device = sys.argv[1]
    writeback_device = sys.argv[2]
    run_all_tests(zram_device, writeback_device)
