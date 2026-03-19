
import sys
import os

# Adjust path to find core modules
sys.path.append(os.getcwd())

from core import zdevice_ctl, os_utils

def check_status_data():
    print("Checking Device Listing...")
    devices = zdevice_ctl.list_devices()
    if not devices:
        print("No ZRAM devices found.")
    
    for dev in devices:
        print(f"\nDevice: {dev.name}")
        print(f"  DiskSize: {dev.disksize}")
        print(f"  DataSize: {dev.data_size}")
        print(f"  ComprSize: {dev.compr_size}")
        print(f"  TotalSize: {dev.total_size}")
        print(f"  MemLimit: {dev.mem_limit}")
        print(f"  MemMax: {dev.mem_used_max}")
        print(f"  SamePages: {dev.same_pages}")
        print(f"  Migrated: {dev.migrated}")
        print(f"  Mountpoint: {dev.mountpoint}")
        print(f"  Ratio: {dev.ratio} (Type: {type(dev.ratio)})")
        print(f"  Streams: {dev.streams}")
        print(f"  Algorithm: {dev.algorithm}")
        
        # Check writeback
        try:
            wb = zdevice_ctl.get_writeback_status(dev.name)
            print(f"  Writeback Device: {wb.backing_dev}")
        except Exception as e:
            print(f"  Writeback Error: {e}")

if __name__ == "__main__":
    # Ensure we are in the project root
    if os.path.basename(os.getcwd()) == "ui":
         os.chdir("..")
    
    # Mock some data via os_utils if needed, but we want live data
    # If no live data, we might need to rely on code inspection.
    # Assuming the environment allows reading sysfs (read-only).
    check_status_data()
