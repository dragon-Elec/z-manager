#!/bin/bash
# Cleanup all zram devices using sysfs (no zramctl dependency)

# Iterate over all existing zram devices using sysfs
for dev_path in /sys/block/zram*; do
  if [ -d "$dev_path" ]; then
    dev_name=$(basename "$dev_path")
    echo "--> Deactivating and resetting ${dev_name}..."
    # Deactivate swap if it's a swap device
    sudo swapoff "/dev/${dev_name}" 2>/dev/null || true
    # Reset the device via sysfs
    echo 1 | sudo tee "${dev_path}/reset" > /dev/null 2>&1 || true
  fi
done
echo "Cleanup complete."
