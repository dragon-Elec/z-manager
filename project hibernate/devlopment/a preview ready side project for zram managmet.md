# Z-Manager: Architecture, Safety, and Implementation Guide

> **Version:** 1.0  
> **Last Updated:** December 14, 2025  
> **Status:** Active Development (Targeting Ubuntu 24.04 / Zorin OS 18)

---

## Table of Contents

1.  [Project Vision and Goals](#1-project-vision-and-goals)
2.  [High-Level Architecture](#2-high-level-architecture)
3.  [Core Module Deep Dive](#3-core-module-deep-dive)
    *   [3.1. `core/os_utils.py` - The System Foundation](#31-coreos_utilspy---the-system-foundation)
    *   [3.2. `core/zdevice_ctl.py` - The ZRAM Brain](#32-corezdevice_ctlpy---the-zram-brain)
    *   [3.3. Other Core Modules](#33-other-core-modules)
4.  [Safety Mechanisms](#4-safety-mechanisms)
5.  [Functional Modules](#5-functional-modules)
6.  [User Interface Architecture](#6-user-interface-architecture)
7.  [Data Flow Examples](#7-data-flow-examples)
8.  [Known Issues and Historical Context](#8-known-issues-and-historical-context)

---

## 1. Project Vision and Goals

Z-Manager is a **graphical Linux utility** designed to provide a user-friendly interface for managing **ZRAM** (Compressed RAM Block Devices). Its primary goals are:

1.  **Simplify ZRAM Configuration:** Abstract away the complexity of `sysfs` writes and `systemd-zram-generator` configuration files into an intuitive GTK/Libadwaita interface.
2.  **Enable Advanced Features:** Provide access to advanced ZRAM features like **writeback devices** (backing a ZRAM device with a physical partition for incompressible data), which are difficult to configure manually.
3.  **Ensure System Safety:** Implement robust safety checks to prevent accidental data loss, such as overwriting partitions that contain existing filesystems.
4.  **Be Cross-Version Compatible:** Use direct `sysfs` interaction for runtime operations to ensure compatibility across different `util-linux` (`zramctl`) versions and distribution releases.

### Why Not Just Use `zramctl`?

The project's research (documented in `assets/RESEARCH_SUMMARY.md` and `assets/zramctl-reset-behavior.md`) revealed that `zramctl` is an **unreliable abstraction**:
*   **`zramctl --reset`:** Has undocumented, destructive behavior that removes the device node from `/dev/`, not just its configuration.
*   **`--writeback-device` flag:** Does not exist on older versions of `util-linux` (e.g., the version shipped with Ubuntu 22.04).
*   **Output Parsing:** The table output of `zramctl` is not machine-friendly and lacks JSON support on older versions.

**Conclusion:** Z-Manager bypasses `zramctl` for critical operations and instead talks directly to the kernel via the `sysfs` interface, which provides a stable, predictable, and universal API.

---

## 2. High-Level Architecture

The application follows a layered architecture, separating concerns into distinct directories:

```
z-manager/
├── z-manager.py          # Entry Point: Initializes GTK App and MainWindow.
│
├── core/                 # THE BRAIN: Low-level system logic.
│   ├── os_utils.py       # Foundation: Shell commands, sysfs I/O, safety checks.
│   ├── zdevice_ctl.py    # Controller: High-level ZRAM device operations.
│   ├── config.py         # Reader: Parses zram-generator.conf.
│   ├── config_writer.py  # Writer: Generates zram-generator.conf content.
│   ├── boot_config.py    # Persistence: Manages sysctl.d and GRUB settings.
│   └── health.py         # Diagnostics: Checks for zswap, sysfs access, etc.
│
├── modules/              # THE SKILLS: Specific functional components.
│   ├── monitoring.py     # Live Stats: Generators for UI dashboards.
│   ├── profiles.py       # Profiles: Manages Desktop/Gaming/Server presets.
│   ├── psi.py            # PSI: Pressure Stall Information monitoring.
│   ├── journal.py        # Logs: Reads systemd journal for ZRAM events.
│   └── runtime.py        # Volatile Tunables: Live sysctl/CPU governor changes.
│
├── ui/                   # THE FACE: GTK/Libadwaita user interface.
│   ├── main_window.py    # Main App Window and Navigation Stack.
│   ├── status_page.py    # Dashboard: Displays device status and stats.
│   ├── configure_page.py # Settings: Device size, algorithm, writeback.
│   ├── tune_page.py      # Kernel Tuning: Swappiness, zswap disable.
│   ├── custom_widgets.py # Custom Widgets: CompressionRing, MemoryTube.
│   ├── device_picker.py  # Dialog: Block device selection for writeback.
│   └── colors.py         # Theming: Material Design 3 color generation.
│
└── assets/               # Documentation and resources.
```

### Entry Point: `z-manager.py`

**Location:** `z-manager.py` (project root)  
**Role:** Application bootstrap and launcher.

This file serves as the executable entry point for Z-Manager. Its responsibilities are minimal by design:

1. **Path Configuration:** Adds the project root to `sys.path` to enable absolute imports like `from core import ...`
2. **GTK Initialization:** Requires GTK 4.0 and Libadwaita 1.0
3. **Application Class:** Defines `ZManagerApp(Adw.Application)` with:
   - Application ID: `com.github.z-manager`
   - `on_activate()` handler that creates and presents `MainWindow`
4. **Signal Handling:** Configures `SIGINT` (Ctrl+C) to terminate gracefully
5. **Main Loop:** Runs `app.run(sys.argv)` to start the GTK event loop

**Design Philosophy:** Keep `z-manager.py` small and delegate all UI logic to `ui/main_window.py`. This makes the codebase more modular and testable.

---

### Dependency Flow

The dependencies flow **downwards**. Higher-level modules depend on lower-level ones, but never the reverse.

*   **`ui/` depends on `modules/` and `core/`**
*   **`modules/` depends on `core/`**
*   **`core/` modules depend on `os_utils.py`** (the foundation)

This structure prevents circular imports and keeps the codebase maintainable.

---

## 3. Core Module Deep Dive

This section provides a detailed analysis of the most critical files in the application.

---

### 3.1. `core/os_utils.py` - The System Foundation

**Path:** `core/os_utils.py`  
**Role:** This is the **lowest-level utility module**. It provides all the primitive functions for interacting with the operating system. No other module in `core/` or `modules/` should directly call `subprocess`, `open()` on system files, or interact with the kernel—they must go through `os_utils`.

#### Key Functions & Their Purpose

| Function | Purpose | Safety Relevance |
| :--- | :--- | :--- |
| `run(cmd, ...)` | Executes a shell command using `subprocess.run`. Returns a `CmdResult` dataclass. | **Low-risk wrapper.** Centralizes all process spawning. |
| `read_file(path)` | Reads the content of a file, typically from `/sys` or `/proc`. Returns `None` on failure. | Used for reading device status. Non-destructive. |
| `sysfs_write(path, value)` | **Writes a value to a `sysfs` file.** This is the core mechanism for configuring ZRAM devices. | **HIGH-RISK.** This is how device parameters are changed. |
| `atomic_write_to_file(path, content)` | Writes content to a file atomically (write to temp, then rename). Used for config files like `zram-generator.conf`. | **MEDIUM-RISK.** Safe for the file itself, but can change system behavior on next boot. |
| `is_block_device(path)` | Checks if a path points to a valid block device. | **SAFETY CHECK.** Used before any writeback operation. |
| `check_device_safety(device_path)` | **THE CRITICAL SAFETY GATE.** Uses `blkid` to check if a device has an existing filesystem. Returns a `DeviceSafetyResult`. | **PRIMARY SAFETY MECHANISM.** Prevents overwriting user data. |
| `list_block_devices()` | Parses `lsblk -J` output to return a list of all block devices and partitions. | Used to populate the device picker dialog. Non-destructive. |
| `parse_size_to_bytes(size_str)` | Converts a human-readable size string (e.g., "4G", "512M") to an integer in bytes. | Used for interpreting user input and config values. |

#### `check_device_safety` - The Data Loss Preventer

This function is the **single most important safety mechanism** in the application. Its job is to prevent the user from accidentally using a partition containing their photos, documents, or OS as a writeback device for ZRAM.

**How it works:**

1.  Takes a device path (e.g., `/dev/sda3`) as input.
2.  Runs the `blkid` command on the device.
3.  Parses the output.
    *   If `blkid` finds a filesystem signature (`TYPE=...`), the device is **NOT SAFE**.
    *   If `blkid` returns nothing or an error (meaning the partition is blank/unformatted), the device is **SAFE** to use.
4.  Returns a tuple `(is_safe: bool, message: str)` where `is_safe` indicates if the device is safe to use, and `message` explains why if it's not safe.

**Example Usage (from `zdevice_ctl.py`):**

```python
from core.os_utils import check_device_safety

is_safe, message = check_device_safety("/dev/sda3")
if not is_safe:
    # Display a warning to the user!
    print(f"DANGER: {message}")
    # Abort the operation.
```

---

### 3.2. `core/zdevice_ctl.py` - The ZRAM Brain

**Path:** `core/zdevice_ctl.py`  
**Role:** This is the **high-level controller** for all ZRAM device operations. It orchestrates calls to `os_utils` and `config_writer` to perform complex, multi-step actions like setting a writeback device on a live system.

#### Key Data Models (Dataclasses)

The module defines several dataclasses to structure its return values, making the code self-documenting:

| Dataclass | Purpose |
| :--- | :--- |
| `DeviceInfo` | Holds all properties of a single ZRAM device (name, disksize, algorithm, streams, usage stats, writeback status). |
| `WritebackStatus` | Details about the writeback of a device: `backing_dev_path`, `bd_stat`, `huge_idle_stat`. |
| `UnitResult` | Result of a `systemctl` operation (restart, stop). Contains `success`, `message`. |
| `WritebackResult` | Result of a `set_writeback` or `clear_writeback` operation. |
| `PersistResult` | Result of persisting configuration to `zram-generator.conf`. |
| `OrchestrationResult` | A high-level result for complex operations, containing nested `WritebackResult` and `PersistResult`. |

#### Key Functions & Orchestration Logic

| Function | Purpose | Complexity |
| :--- | :--- | :--- |
| `list_devices()` | Scans `/sys/block/zram*` and returns a list of `DeviceInfo` for all active ZRAM devices. | Low. Read-only. |
| `get_writeback_status(device_name)` | Reads `backing_dev`, `bd_stat`, etc. from sysfs for a device. | Low. Read-only. |
| `_ensure_device_exists(device_name)` | If the device node doesn't exist, creates it using `cat /sys/class/zram-control/hot_add`. | Medium. Creates resources. |
| `_reconfigure_device_sysfs(...)` | The core reconfiguration logic. Writes `comp_algorithm`, `disksize`, `backing_dev` to sysfs in the **correct order**. | High. Destructive if misused. |
| `set_writeback(device_name, backing_dev, force)` | **THE MAIN ORCHESTRATOR.** Sets a writeback device. If `force=True`, it will `swapoff`, `reset`, and reconfigure the device. | **VERY HIGH.** This is the most complex and potentially dangerous function. |
| `clear_writeback(device_name)` | Removes the writeback device. Requires a reset. | High. Destructive. |
| `persist_writeback(device_name, backing_dev)` | Writes the configuration to `/etc/systemd/zram-generator.conf` for persistence across reboots. | Medium. Changes boot behavior. |

#### The `set_writeback` Orchestration - A Step-by-Step Breakdown

This function demonstrates the complexity involved in changing a writeback device on a live, active ZRAM device.

**Scenario:** User wants to set `/dev/sda3` as the writeback device for `zram0`, which is currently active as swap.

**Orchestration Steps (when `force=True`):**

1.  **Safety Check:** Call `os_utils.check_device_safety("/dev/sda3")`. **ABORT** if a filesystem is found.
2.  **Get Current State:** Read current `disksize`, `comp_algorithm` from `/sys/block/zram0/*`. These values must be preserved.
3.  **Graceful Deactivation (`swapoff`):**
    *   Run `sudo swapoff /dev/zram0`.
    *   This tells the kernel to move all compressed data from `zram0` back to physical RAM.
    *   **If this fails** (not enough free RAM), the operation can still proceed if `force=True`, but data loss may occur.
4.  **Reset Device:**
    *   Write `1` to `/sys/block/zram0/reset`.
    *   This clears the device's configuration, making it a blank slate. All data is lost at this point.
5.  **Reconfigure (Correct Order is Critical!):**
    *   Write the compression algorithm: `echo zstd > /sys/block/zram0/comp_algorithm`.
    *   Write the **backing device FIRST**: `echo /dev/sda3 > /sys/block/zram0/backing_dev`.
    *   Write the disksize **LAST**: `echo 4G > /sys/block/zram0/disksize`.
    *   (Failure to set `backing_dev` before `disksize` will result in an `EBUSY` error.)
6.  **Reactivate (`swapon`):**
    *   Run `sudo mkswap /dev/zram0`.
    *   Run `sudo swapon -p 100 /dev/zram0`.
7.  **Return Result:** Return an `OrchestrationResult` with success/failure status and messages.

---

### 3.3. Other Core Modules

| Module | Purpose |
| :--- | :--- |
| `core/config.py` | Reads and parses the INI-style `zram-generator.conf` file using `configparser`. Provides `read_zram_config()` and `apply_config_with_restart()`. |
| `core/config_writer.py` | Generates the content string for `zram-generator.conf`. Provides `generate_config_string()` and `update_config_param()`. Used by `zdevice_ctl.persist_writeback()`. |
| `core/boot_config.py` | Manages persistent system tuning. Writes to `/etc/sysctl.d/` for kernel parameters and `/etc/default/grub.d/` for boot-time flags like `zswap.enabled=0`. |
| `core/health.py` | Performs system health checks. Detects if `zswap` is enabled (a conflict with ZRAM), checks `sysfs` accessibility, and lists all swap devices from `/proc/swaps`. |

---

## 4. Safety Mechanisms

Z-Manager is designed to interact with low-level kernel subsystems. Several layers of safety are implemented:

### 4.1. Pre-Operation Device Safety Check

*   **Where:** `core/os_utils.check_device_safety()`
*   **What:** Before *any* writeback operation, the target device is scanned with `blkid` to detect existing filesystems.
*   **Action:** If a filesystem (ext4, ntfs, btrfs, etc.) is detected, the operation is **blocked**, and the user is shown a warning in the UI.

### 4.2. Graceful `swapoff` Attempt

*   **Where:** `core/zdevice_ctl.set_writeback()` / `clear_writeback()`
*   **What:** Before resetting a device, the application attempts a graceful `swapoff`. This moves all data from the ZRAM device back to physical RAM.
*   **Limitation:** If there is not enough free RAM, `swapoff` will fail. The `force=True` flag allows proceeding anyway, which can cause data loss for the data trapped in ZRAM.

### 4.3. Safe Reset via Sysfs

*   **Where:** `core/zdevice_ctl._reconfigure_device_sysfs()`
*   **What:** The application uses `echo 1 > /sys/block/zramN/reset` instead of `zramctl --reset`.
*   **Why:** The `zramctl` command has undocumented behavior that **deletes the device node entirely**. The `sysfs` method only clears the configuration, preserving the `/dev/zramN` node.

### 4.4. Atomic Configuration File Writes

*   **Where:** `core/os_utils.atomic_write_to_file()`
*   **What:** When writing configuration files (like `zram-generator.conf` or `sysctl.d` files), the application writes to a temporary file first, then uses `os.rename()` to atomically replace the original.
*   **Why:** This prevents file corruption if the application crashes or is killed mid-write.

### 4.5. Configuration Order Enforcement

*   **Where:** `core/zdevice_ctl._reconfigure_device_sysfs()`
*   **What:** The kernel requires that `backing_dev` is set **before** `disksize`. The application enforces this order internally, preventing a common user error.

---

## 5. Functional Modules - Detailed Analysis

These modules in `modules/` provide "skills" that the UI and other parts of the application consume.

---

### 5.1. `modules/monitoring.py` - Real-Time Stats Engine

**Purpose:** Provides Python **generator functions** that yield data at regular intervals, designed to be consumed by `GLib.timeout_add()` for live UI updates.

**Key Functions:**

| Function | Yields | Interval | Data Source |
| :--- | :--- | :--- | :--- |
| `watch_device_usage(device_name)` | Uncompressed data size (bytes) | Configurable | `zdevice_ctl.get_writeback_status()` |
| `watch_system_stats()` | `SystemStats` NamedTuple with `cpu_percent`, `memory_percent`, `memory_used`, `memory_total` | Configurable | `psutil.cpu_percent()`, `psutil.virtual_memory()` |

**Dependency:** Requires `psutil` for system stats. If `psutil` is not installed, `watch_system_stats` will fail gracefully.

**Usage Pattern (in UI):**
```python
# In StatusPage.refresh()
for usage in monitoring.watch_device_usage("zram0"):
    self.memory_tube.set_zram_usage(usage)
    break  # Only get one value per refresh cycle
```

---

### 5.2. `modules/profiles.py` - Configuration Presets

**Purpose:** Manages ZRAM configuration profiles that bundle together settings like size, algorithm, and kernel tunables.

**Profile Storage:**

| Type | Location | Editable |
| :--- | :--- | :--- |
| Built-in | Hardcoded in `profiles.py` | No |
| User-defined | `~/.config/zman/profiles/*.json` | Yes |

**Built-in Profiles:**

1.  **Desktop / Gaming (Recommended):**
    *   `zram-size`: `ram` (100% of RAM)
    *   `compression-algorithm`: `zstd`
    *   `swap-priority`: 100
2.  **Server (Conservative):**
    *   `zram-size`: `min(ram / 2, 8192)`
    *   `compression-algorithm`: `lzo-rle` (lower CPU)
    *   `swap-priority`: 75

**Key Functions:**

| Function | Purpose |
| :--- | :--- |
| `get_all_profiles()` | Returns a merged dict of built-in and user profiles. |
| `load_profile(name)` | Returns the full profile dict for a given name. |
| `save_profile(name, data)` | Saves a user profile as JSON. |
| `delete_profile(name)` | Deletes a user profile (built-ins are protected). |

---

### 5.3. `modules/psi.py` - Pressure Stall Information

**Purpose:** Reads kernel PSI metrics to detect system resource contention. PSI is a modern Linux feature (kernel 4.20+) that reports how much time tasks are stalled waiting for CPU, memory, or I/O.

**Data Sources:**

*   `/proc/pressure/cpu`
*   `/proc/pressure/memory`
*   `/proc/pressure/io`

**Key Functions:**

| Function | Purpose |
| :--- | :--- |
| `get_psi()` | Returns a snapshot `{"cpu": {...}, "memory": {...}, "io": {...}}`. |
| `watch_psi(interval)` | Generator that yields PSI snapshots at a given interval. |

**PSI Data Format (per resource):**
```
some avg10=0.00 avg60=0.00 avg300=0.00 total=12345
full avg10=0.00 avg60=0.00 avg300=0.00 total=6789
```
*   `some`: At least one task was stalled.
*   `full`: All tasks were stalled (resource fully saturated).

**UI Integration:** The Tune Page can display PSI metrics to help users understand if their system is under memory pressure.

---

### 5.4. `modules/journal.py` - Systemd Log Reader

**Purpose:** Retrieves log entries from the systemd journal, specifically for ZRAM-related services like `systemd-zram-setup@zram0.service`.

**Implementation Strategy:**

1.  **Preferred:** Uses `systemd.journal.Reader` from the `python3-systemd` package for direct, efficient access.
2.  **Fallback:** If `python3-systemd` is not available, it parses the text output of `journalctl -u <unit> --no-pager -n <limit>`.

**Key Functions:**

| Function | Purpose |
| :--- | :--- |
| `list_zram_logs(unit, limit)` | Returns a list of `JournalRecord` dataclasses. |

**`JournalRecord` Fields:**

*   `timestamp`: `datetime` object.
*   `priority`: Log level (e.g., `info`, `warning`, `error`).
*   `message`: The log message text.

---

### 5.5. `modules/runtime.py` - Volatile Kernel Tunables

**Purpose:** Manages live, non-persistent system settings. Changes made via this module are lost on reboot. For persistent changes, see `core/boot_config.py`.

**Key Functions:**

| Function | Target Path | Notes |
| :--- | :--- | :--- |
| `get_cpu_governor()` | `/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Returns current governor (e.g., `powersave`). |
| `set_cpu_governor(gov)` | (All CPUs) | Sets governor on all CPU cores. |
| `get_io_scheduler(device)` | `/sys/block/<dev>/queue/scheduler` | Returns current scheduler. |
| `set_io_scheduler(device, sched)` | (Same) | Sets scheduler (e.g., `mq-deadline`). |
| `get_vfs_cache_pressure()` | `/proc/sys/vm/vfs_cache_pressure` | Default is 100. |
| `set_vfs_cache_pressure(val)` | (Same) | Higher = more aggressive cache reclaim. |

---

## 6. User Interface Architecture - Detailed Breakdown

---

### 6.1. Entry Point: `z-manager.py`

This is a minimal script that:
1.  Creates an `Adw.Application` instance.
2.  Connects the `activate` signal to a handler that creates and shows `MainWindow`.
3.  Runs the GTK main loop.

---

### 6.2. Main Window: `ui/main_window.py`

**Class:** `MainWindow(Adw.ApplicationWindow)`

**Responsibilities:**
*   Creates the custom header bar with navigation buttons (Status, Configure, Tune) and window control buttons (Minimize, Maximize, Close).
*   Hosts a `Gtk.Stack` as the main content area.
*   Loads and adds the three page widgets to the stack.
*   Loads the application CSS from `css/style.css`.

**Navigation Logic:**
*   Each navigation button has a `clicked` signal connected to a handler that calls `self.stack.set_visible_child_name("status")` (or "configure", "tune").

---

### 6.3. Status Page: `ui/status_page.py` & `status_page.ui`

**Purpose:** The main dashboard displaying real-time ZRAM status.

**UI Structure (from `.ui` file):**
*   `AdwPreferencesGroup` "Health Alerts": Contains an `AdwBanner` for warnings (e.g., zswap enabled).
*   `AdwPreferencesGroup` "Active ZRAM Devices": Dynamically populated with device cards.
*   `AdwPreferencesGroup` "All System Swap Devices": Lists all swaps from `/proc/swaps`.
*   `AdwPreferencesGroup` "System Health Events": Displays recent journal logs.

**Python Logic (`status_page.py`):**
*   `__init__`: Calls `self.refresh()` and sets up a 5-second timer.
*   `refresh()`: Calls `zdevice_ctl.list_devices()`, `health.get_all_swaps()`, and `journal.list_zram_logs()`. Updates widgets accordingly.
*   `_create_device_card(device_info)`: Dynamically creates an `AdwExpanderRow` containing `CompressionRing` and `MemoryTube` for each device.

---

### 6.4. Configure Page: `ui/configure_page.py` & `configure_page.ui`

**Purpose:** Settings for ZRAM configuration—size, algorithm, writeback device.

**UI Structure (from `.ui` file):**
*   `AdwPreferencesGroup` "Configuration Profiles": A `GtkFlowBox` populated with `ScenarioCard` widgets.
*   `AdwPreferencesGroup` "Basic Settings": `AdwComboRow` for size mode and algorithm, `AdwSpinRow` for priority.
*   `AdwPreferencesGroup` "Activation Rules": `AdwSwitchRow` for host memory limit toggle.
*   `AdwPreferencesGroup` "Advanced Settings": `AdwExpanderRow` containing filesystem mode toggle, writeback device selector.
*   `GtkActionBar`: "Revert" and "Apply Changes" buttons.

**Python Logic (`configure_page.py`):**
*   `_populate_profiles()`: Creates `ScenarioCard` widgets from `profiles.get_all_profiles()`.
*   `on_select_writeback_clicked()`: Opens `DevicePickerDialog`.
*   `on_apply_clicked()`: Gathers all settings, calls `zdevice_ctl.set_writeback()` / `persist_writeback()`, and restarts the systemd unit.

---

### 6.5. Tune Page: `ui/tune_page.py` & `tune_page.ui`

**Purpose:** Kernel tuning options for swappiness, PSI, and zswap conflict resolution.

**UI Structure (from `.ui` file):**
*   `AdwPreferencesGroup` "Performance Profile": Toggle for enabling recommended `sysctl` settings.
*   `AdwPreferencesGroup` "Advanced Kernel Tuning": `AdwSpinRow` for `vfs_cache_pressure`.
*   `AdwPreferencesGroup` "PSI Monitoring": Switches for CPU, Memory, I/O PSI.
*   `AdwPreferencesGroup` "ZSwap Conflict Resolution": Button to disable zswap via GRUB, with a warning banner.

**Python Logic (`tune_page.py`):** Currently minimal; most logic is handled by signal connections defined in the `.ui` file or to be implemented.

---

### 6.6. Custom Widgets: `ui/custom_widgets.py`

**`CompressionRing(Gtk.DrawingArea)`:**
*   Draws a donut chart showing the compression ratio.
*   `set_ratio(ratio)`: Updates the displayed value (e.g., `3.5x`).
*   Uses Cairo for drawing. Colors are dynamically generated from MD3 palette.

**`MemoryTube(Gtk.DrawingArea)`:**
*   Draws a horizontal stacked bar chart.
*   Segments: "App Used" (physical RAM), "ZRAM Used", "Free".
*   `set_values(app_used, zram_used, free)`: Updates the bar proportions.

**`ScenarioCard(Gtk.ToggleButton)`:**
*   A styled card for profile selection.
*   Displays an icon, title, and description.
*   Part of a `Gtk.FlowBox` in ConfigurePage.

---

### 6.7. Device Picker: `ui/device_picker.py`

**Class:** `DevicePickerDialog(Adw.Window)`

**Purpose:** A modal dialog for selecting a block device to use as a writeback backing device.

**Flow:**
1.  On open, calls `os_utils.list_block_devices()`.
2.  Displays devices in an `AdwPreferencesGroup` with `AdwActionRow` per device.
3.  User clicks a device.
4.  Dialog calls `os_utils.check_device_safety()`.
5.  If unsafe, shows a warning; user can cancel or force.
6.  If safe (or forced), returns the device path to the caller.

---

### 6.8. Color Theming: `ui/colors.py`

**Purpose:** Implements Material Design 3 (MD3) dynamic color generation.

**How it works:**
1.  Takes a base accent color (e.g., from system theme or user choice).
2.  Converts RGBA to HSLA.
3.  Generates tonal palettes (Primary, Secondary, Tertiary, Neutral) by shifting lightness.
4.  Maps tones to MD3 semantic roles (e.g., `primary`, `on-primary`, `surface`, `on-surface`) for both light and dark themes.

**Used by:** `CompressionRing`, `MemoryTube`, and potentially CSS variables.

---

## 7. Configuration Files Reference

### 7.1. `zram-generator.conf`

**Path:** `/etc/systemd/zram-generator.conf`
**Managed by:** `core/config.py`, `core/config_writer.py`

**Format:** INI-style with sections per device.

```ini
[zram0]
zram-size = min(ram, 8192)
compression-algorithm = zstd
swap-priority = 100
writeback-device = /dev/sda3  # Requires zram-generator 1.1.0+
```

### 7.2. Sysctl Files

**Path:** `/etc/sysctl.d/99-zman-*.conf`
**Managed by:** `core/boot_config.py`

```ini
vm.swappiness = 180
vm.page-cluster = 0
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
```

### 7.3. GRUB Config

**Path:** `/etc/default/grub.d/99-zman-*.cfg`
**Managed by:** `core/boot_config.py`

Used to set:
*   `zswap.enabled=0` - Disable zswap (conflicts with ZRAM).
*   `psi=1` - Enable PSI (if not enabled by default).

---

## 8. Data Flow Examples

### Example 1: Displaying ZRAM Status on Launch

1.  `StatusPage.__init__()` is called.
2.  It schedules a `GLib.timeout_add_seconds()` to call `self.refresh()` every 5 seconds.
3.  `refresh()` calls `core.zdevice_ctl.list_devices()`.
4.  `list_devices()` scans `/sys/block/` for `zram*` directories.
5.  For each device, it reads `disksize`, `comp_algorithm`, `orig_data_size`, `compr_data_size`, etc. using `os_utils.read_file()`.
6.  It returns a list of `DeviceInfo` dataclasses.
7.  `refresh()` iterates over the list and creates/updates `CompressionRing` and `MemoryTube` widgets for each device.

### Example 2: User Selects a Writeback Device

1.  User clicks "Select Disk" button on `ConfigurePage`.
2.  `on_select_writeback_clicked()` opens `DevicePickerDialog`.
3.  `DevicePickerDialog.__init__()` calls `os_utils.list_block_devices()`.
4.  It displays a list of available partitions.
5.  User selects `/dev/sda3`.
6.  Dialog calls `os_utils.check_device_safety("/dev/sda3")`.
7.  **If unsafe:** A warning is shown. User must confirm or cancel.
8.  **If safe:** Dialog returns the selected device path.
9.  `ConfigurePage` stores the selection and enables the "Apply" button.
10. User clicks "Apply".
11. `ConfigurePage` calls `zdevice_ctl.set_writeback("zram0", "/dev/sda3", force=True)`.
12. (The orchestration described in Section 3.2 happens here).
13. UI is refreshed to show the new writeback status.

---

## 8. Known Issues and Historical Context

This section summarizes findings from the `assets/` documentation.

### 8.1. Ubuntu 22.04 Incompatibility (On Hold)

*   **Issue:** The `systemd-zram-generator` version in Ubuntu 22.04 (0.3.2) does **not** support the `writeback-device=` option in `zram-generator.conf`.
*   **Impact:** Persistent writeback configuration is not possible on 22.04. Only runtime (non-persistent) writeback can be set via sysfs.
*   **Resolution:** Development resumed targeting Ubuntu 24.04 / Zorin OS 18, which ships `zram-generator` 1.1.2+.

### 8.2. `zramctl --reset` is Destructive

*   **Issue:** The command removes the `/dev/zramN` node entirely, not just its configuration.
*   **Impact:** Z-Manager uses the `sysfs` reset method (`echo 1 > .../reset`) instead.

### 8.3. GTK Focus Crash with `Adw.ActionRow` in `Gtk.Box`

*   **Issue:** Placing `Adw.ActionRow` (a list-item widget) inside a `Gtk.Box` causes `Gtk-CRITICAL` errors related to focus management.
*   **Impact:** The event log in `StatusPage` was refactored to use a different widget type.

### 8.4. Swap Files Cannot Be Writeback Devices

*   **Issue:** The Linux kernel only supports **block device partitions** as writeback backing devices, not regular files.
*   **Workaround:** A loop device can be set up on a file. This is not automated by Z-Manager.

