# ZRAM Research Summary

**Consolidated from:** writeback bheaviour.md, zramctl-reset-behavior.md, how i seted a writeback device.txt, research.txt, erros.md, reminders.md, later bugs.txt

---

## 1. Key Discoveries

### zramctl Is Unreliable ⚠️
- `--reset` **deletes the device node** (undocumented!)
- No `--writeback-device` flag on old Ubuntu versions
- No JSON output support (even on Ubuntu 24.04)
- **Solution:** Use sysfs directly for configuration

### Configuration Order Matters
```
WRONG: disksize → backing_dev  (FAILS with -EBUSY)
RIGHT: backing_dev → disksize  (Works!)
```

### Creating ZRAM Devices
```bash
# Use cat (NOT echo) to create device
sudo cat /sys/class/zram-control/hot_add  # Returns device ID

# Use echo to remove
echo X > /sys/class/zram-control/hot_remove
```

---

## 2. Working Writeback Setup

**Tested working command sequence:**
```bash
sudo modprobe zram
sudo cat /sys/class/zram-control/hot_add
sudo bash -c 'echo /dev/sda2 > /sys/block/zram0/backing_dev'
sudo bash -c 'echo 4G > /sys/block/zram0/disksize'
sudo mkswap /dev/zram0
sudo swapon /dev/zram0 -p 100
```

**Verification:**
```bash
zramctl                            # Shows device info
cat /sys/block/zram0/backing_dev   # Shows backing device
swapon --show                      # Shows active swaps
```

---

## 3. Writeback Requirements

- ✅ Partitions work
- ✅ Loop devices work (create .img → losetup)
- ❌ Swap files DO NOT work directly
- Must set BEFORE disksize
- Cannot change on active device (must reset first)

---

## 4. Safe Reset vs Destructive Reset

**sysfs reset (SAFE - preserves /dev node):**
```bash
echo 1 > /sys/block/zram0/reset
```

**zramctl reset (DANGEROUS - deletes /dev node):**
```bash
zramctl --reset /dev/zram0  # DELETES /dev/zram0!
```

---

## 5. swapoff Behavior

- Returns compressed data to RAM
- **Fails if not enough free RAM**
- TTY workaround: Ctrl+Alt+F3 → log in → swapoff (less RAM used)
- `force=True` mode proceeds with reset even if swapoff fails (data loss risk)

---

## 6. Ubuntu Version Compatibility

| Ubuntu | zram-generator | Writeback Config | zramctl JSON |
|--------|---------------|-----------------|--------------|
| 22.04 | 0.3.2 | ❌ No | ❌ No |
| 24.04 | 1.1.2 | ✅ Yes | ❌ No |

---

## 7. Architecture Decisions

**Full Sysfs approach (implemented):**
- sysfs for **reading** device list (parsing `/sys/block/zram*` directly)
- sysfs for **writing** configuration (reliable)

**Why:** Shifted to pure sysfs because it is "overall honest" — it represents the true kernel state without the abstraction or version-dependency faults of `zramctl`.

---

## 8. Fixed Issues

- ✅ parse_size_to_bytes handles G and GiB
- ✅ Circular dependency removed (config_writer.py created)
- ✅ File I/O centralized in os_utils.py
- ✅ GTK ActionRow used in proper containers
- ✅ psutil integrated for monitoring

---

## 9. Debugging Commands

```bash
# Service status
sudo systemctl status systemd-zram-setup@zram0.service

# Logs
sudo journalctl -u "systemd-zram-setup@*" --no-pager

# Check config
cat /etc/systemd/zram-generator.conf

# List swaps
swapon --show
cat /proc/swaps
```

---

## 10. Current Project Status

**Environment:** Zorin OS 18 / Ubuntu 24.04
**systemd-zram-generator:** 1.1.2 ✅ (writeback config supported!)
**Status:** Ready to resume development

---

*Last updated: December 2025*
