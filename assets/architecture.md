# Z-Manager Architecture

> **High-Level System Design**  
> **Last Updated:** December 14, 2025

---

## Overview

Z-Manager is a GTK/Libadwaita application for managing ZRAM devices on Linux. It provides a user-friendly interface for advanced ZRAM features like writeback devices while ensuring system safety through multiple validation layers.

**Entry Point:** `z-manager.py` - Launches the GTK application, initializes the Adwaita Application instance, and displays the main window.

**Core Philosophy:** Direct `sysfs` interaction for portability across different `util-linux` versions, avoiding unreliable `zramctl` abstractions.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (GTK 4 + Libadwaita)        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Status Page  │  │Configure Page│  │  Tune Page   │  │
│  │ (Dashboard)  │  │  (Settings)  │  │  (Kernel)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Functional Modules                     │
│  ┌────────┐ ┌─────────┐ ┌──────┐ ┌─────────┐ ┌──────┐  │
│  │Monitor │ │Profiles │ │ PSI  │ │ Journal │ │Runtime│ │
│  └────────┘ └─────────┘ └──────┘ └─────────┘ └──────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      Core Layer                          │
│  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌──────────┐   │
│  │os_utils  │ │zdevice_ctl │ │ config │ │boot_config│  │
│  │(Foundation)│ │(Controller)│ │(Reader)│ │(Persist) │  │
│  └──────────┘ └────────────┘ └────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Dependency Flow:** Strictly downward — UI → Modules → Core. No circular dependencies.

---

## Application Entry Point

### `z-manager.py`

**Purpose:** Application launcher and initialization script.

**Responsibilities:**

- Creates the `Adw.Application` instance with application ID `com.github.z-manager`
- Configures signal handling (allows Ctrl+C to terminate)
- Connects to GTK's `activate` signal to instantiate `MainWindow`
- Runs the GTK main event loop

**Note:** This is a minimal bootstrap script. All UI logic resides in `ui/main_window.py`.

---

## Core Components

### 1. Core Layer (`core/`)

The foundational layer that directly interacts with the kernel and system.

| Module                 | Responsibility                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------- |
| **`os_utils.py`**      | System primitives: subprocess execution, sysfs I/O, block device discovery, **safety checks**           |
| **`zdevice_ctl.py`**   | High-level ZRAM orchestration: device lifecycle, writeback configuration, complex multi-step operations |
| **`config.py`**        | Reads `zram-generator.conf`, parses systemd configuration                                               |
| **`config_writer.py`** | Generates configuration file content for persistence                                                    |
| **`boot_config.py`**   | Manages persistent settings via `/etc/sysctl.d/` and `/etc/default/grub.d/`                             |
| **`health.py`**        | System health diagnostics: zswap detection, sysfs accessibility, swap device enumeration                |

**Key Design:** All kernel interaction funnels through `os_utils.py` to centralize error handling and provide a stable abstraction.

### 2. Functional Modules (`modules/`)

Specialized capabilities consumed by the UI.

| Module              | Purpose                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| **`monitoring.py`** | Real-time data generators for live UI updates (uses `psutil`)          |
| **`profiles.py`**   | Configuration presets (built-in + user-defined JSON files)             |
| **`psi.py`**        | Pressure Stall Information monitoring for memory pressure detection    |
| **`journal.py`**    | Systemd journal log retrieval (python3-systemd or journalctl fallback) |
| **`runtime.py`**    | Volatile system tunables (CPU governor, I/O scheduler, sysctl values)  |

### 3. UI Layer (`ui/`)

GTK 4 + Libadwaita interface with Material Design 3 theming.

| Component               | Description                                                                 |
| ----------------------- | --------------------------------------------------------------------------- |
| **`main_window.py`**    | Application shell: header bar, navigation stack, CSS loading                |
| **`status_page.py`**    | Real-time dashboard showing device status and system health                 |
| **`configure_page.py`** | Settings for ZRAM size, algorithm, writeback device, profiles               |
| **`tune_page.py`**      | Kernel tuning: swappiness, PSI, zswap conflict resolution                   |
| **`custom_widgets.py`** | Custom Cairo-drawn widgets: `CompressionRing`, `MemoryTube`, `ScenarioCard` |
| **`device_picker.py`**  | Modal dialog for safe block device selection                                |
| **`colors.py`**         | MD3 dynamic color palette generation from accent color                      |

---

## Safety Architecture

Z-Manager implements multiple safety layers to prevent data loss:

### 1. Pre-Flight Device Validation

- **`check_device_safety()`** uses `blkid` to detect existing filesystems before any writeback operation
- Blocks operations on partitions containing ext4, ntfs, btrfs, or any other filesystem
- Requires explicit user override for unsafe devices

### 2. Graceful Degradation

- Attempts `swapoff` before device reset to preserve data in RAM
- Falls back safely if insufficient memory available
- Atomic configuration file writes (temp file + rename)

### 3. Order Enforcement

- Kernel requires `backing_dev` set **before** `disksize`
- `zdevice_ctl._reconfigure_device_sysfs()` enforces correct sequence internally
- Prevents common user configuration errors

### 4. Direct Sysfs Usage

- Avoids `zramctl --reset` which deletes device nodes entirely
- Uses `echo 1 > /sys/block/zramN/reset` for safe, predictable behavior

---

## Data Flow Example: Setting a Writeback Device

**User Action:** Selects `/dev/sda3` as writeback device for `zram0`

```
1. UI (configure_page.py)
   └─> Opens DevicePickerDialog
       └─> Calls os_utils.list_block_devices()

2. User selects device
   └─> os_utils.check_device_safety("/dev/sda3")
       ├─ blkid check → filesystem found? → ABORT or WARN
       └─ Safe → Continue

3. UI calls zdevice_ctl.set_writeback("zram0", "/dev/sda3", force=True)
   └─> Orchestration steps:
       a. Read current config (disksize, algorithm)
       b. swapoff /dev/zram0
       c. echo 1 > /sys/block/zram0/reset
       d. echo zstd > comp_algorithm
       e. echo /dev/sda3 > backing_dev  ← MUST be before disksize
       f. echo 4G > disksize
       g. mkswap /dev/zram0
       h. swapon -p 100 /dev/zram0

4. UI calls persist_writeback() [optional]
   └─> config_writer.update_writeback_config()
       └─> os_utils.atomic_write_to_file("/etc/systemd/zram-generator.conf")
           └─> systemd_daemon_reload()
```

---

## Configuration Management

### Runtime vs. Persistent

| Type             | Mechanism               | Persistence                 |
| ---------------- | ----------------------- | --------------------------- |
| **Runtime-only** | Direct sysfs writes     | Lost on reboot              |
| **Persistent**   | `zram-generator.conf`   | Survives reboot via systemd |
| **Boot-time**    | GRUB cmdline + sysctl.d | Applied at boot             |

### Configuration Files

```
/etc/systemd/zram-generator.conf
├─ [zram0]
├─ zram-size = min(ram, 8192)
├─ compression-algorithm = zstd
├─ swap-priority = 100
└─ writeback-device = /dev/sda3  # Ubuntu 24.04+ only

/etc/sysctl.d/99-z-manager.conf
├─ vm.swappiness = 180
├─ vm.page-cluster = 0
└─ vm.watermark_scale_factor = 125

/etc/default/grub.d/99-z-manager-*.cfg
├─ zswap.enabled=0  # Disable conflicting kernel feature
└─ psi=1            # Enable Pressure Stall Information
```

---

## Key Design Decisions

### 1. Why Not Use `zramctl`?

Research (`assets/RESEARCH_SUMMARY.md`, `assets/zramctl-reset-behavior.md`) revealed:

- `--reset` has undocumented destructive behavior (removes device node)
- `--writeback-device` flag doesn't exist on older versions (Ubuntu 22.04)
- JSON output not available on all versions

**Solution:** Direct sysfs interaction provides universal, predictable API.

### 2. Why Generators for Monitoring?

Python generators (`watch_device_usage()`, `watch_system_stats()`) integrate cleanly with GTK's event loop via `GLib.timeout_add()`, avoiding threading complexity.

---

## Platform Support

**Target:** Ubuntu 24.04 / Zorin OS 18

**Requirements:**

- Linux kernel 4.14+ (ZRAM writeback support)
- systemd-zram-generator 1.1.0+ (for `writeback-device=` config option)
- GTK 4 + Libadwaita 1.0+
- Python 3.10+

**Optional Dependencies:**

- `psutil` (system stats monitoring)
- `python3-systemd` (native journal access)

---

## Known Limitations

1. **Ubuntu 22.04:** Cannot persist writeback config (zram-generator too old)
2. **Swap Files:** Cannot be used as writeback devices (kernel limitation), only block devices
3. **Memory Pressure:** `swapoff` fails if insufficient RAM to decompress data

---

## Extension Points

- **Custom Profiles:** JSON files in `~/.config/zman/profiles/`
- **Custom Widgets:** Implement `Gtk.DrawingArea` with Cairo
- **New Modules:** Place in `modules/`, follow dependency rules
- **Theming:** Modify `css/style.css` and `ui/colors.py`
