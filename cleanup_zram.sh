#!/bin/bash
# This loop iterates over all existing zram devices
for dev in $(zramctl --output NAME --noheadings); do
  echo "--> Deactivating and resetting ${dev}..."
  sudo swapoff "${dev}" || true  # Deactivate swap, ignore error if not a swap device
  sudo zramctl --reset "${dev}" || true # Reset the device
done
echo "Cleanup complete."

