# Project Blueprint: Z-Manager & Hibernation Extension

> **Status:** Draft / Planning
> **Target OS:** Ubuntu 24.04, Zorin OS 18 (Debian-based)
> **Goal:** Create a unified GUI for managing ZRAM (runtime performance) and Hibernation (power saving), implementing a "Split-Horizon" memory architecture.

---

## 1. Architectural Vision

The project unifies two conflicting goals: **High-speed volatile swapping** (ZRAM) and **Persistent state saving** (Hibernation).

### The "Split-Horizon" Strategy
To make these work together, the system enforces a strict priority hierarchy managed by the kernel:
1.  **Tier 1: ZRAM (Priority 100)**
    *   **Role:** Active runtime swap. Stores compressed working pages.
    *   **Behavior:** Fast, volatile (lost on power loss).
    *   **Manager:** `systemd-zram-generator`.
2.  **Tier 2: Disk Swap (Priority 0)**
    *   **Role:** Idle overflow & Hibernation backing store.
    *   **Behavior:** Slow, persistent. Remained empty during normal usage due to low priority.
    *   **Manager:** `/etc/fstab` + `hibernate_ctl.py`.

### System Logic Flow
1.  **Boot:** Initramfs loads `resume` module -> Kernel restores S4 image from disk (if exists) -> System boots.
2.  **Runtime:** Apps use RAM. Memory pressure triggers swapping to ZRAM (Prio 100). Disk swap (Prio 0) is untouched.
3.  **Suspend (S3):** System sleeps to RAM. ZRAM stays alive.
4.  **Hibernate (S4):** `Suspend-Then-Hibernate` triggers. RAM (including ZRAM content) is written to Disk Swap. System powers off.

---

## 2. Directory Structure & File Inventory

The codebase is organized into a modular hierarchy.

```
project-hibernate/
├── z-manager.py                  # Entry Point
├── blueprint.md                  # This file
├── core/                         # Low-level Logic & Controllers
│   ├── os_utils.py               # Shell/Sysfs primitives
│   ├── zdevice_ctl.py            # ZRAM Device Controller
│   ├── hibernate_ctl.py          # [NEW] Hibernation Controller
│   ├── config.py                 # Config Reader
│   ├── config_writer.py          # Config Writer
│   ├── boot_config.py            # Bootloader/Kernel Params
│   └── health.py                 # Diagnostics
├── modules/                      # Functional Skills
│   ├── sleep_config.py           # [NEW] Systemd Sleep/Logind Config
│   ├── monitoring.py             # Stats Generators
│   ├── profiles.py               # ZRAM Presets
│   ├── psi.py                    # Pressure Stall Info
│   ├── journal.py                # Log Reader
│   └── runtime.py                # Volatile Tunables
├── ui/                           # GTK4 / Libadwaita Interface
│   ├── main_window.py            # App Window & Stack
│   ├── status_page.py            # Dashboard
│   ├── configure_page.py         # ZRAM Settings
│   ├── hibernate_page.py         # [NEW] Hibernation Setup & Settings
│   ├── tune_page.py              # Kernel Tunables
│   ├── custom_widgets.py         # Visualizations
│   ├── device_picker.py          # Partition Selector
│   └── colors.py                 # Dynamic Theming
└── assets/                       # Resources
```

---

## 3. Module Details

### 3.1 Entry Point
*   **`z-manager.py`**:
    *   Bootstraps the `Adw.Application`.
    *   Sets up the Python path.
    *   Instantiates `MainWindow`.

### 3.2 Core Modules (The Brain)

#### `core/os_utils.py` (Existing)
*   **Purpose:** The ONLY place where `subprocess` or direct file I/O should happen.
*   **Key Functions:**
    *   `run(cmd)`: Execute shell commands safely.
    *   `sysfs_write(path, value)`: Write to kernel interfaces.
    *   `check_device_safety(path)`: **CRITICAL**. Checks `blkid` to prevent overwriting data partitions.
    *   **[UPDATE]** `get_partition_uuid(path)`: Extract UUID for bootloader config.
    *   **[UPDATE]** `get_fs_type(path)`: Detect Ext4 vs Btrfs.

#### `core/zdevice_ctl.py` (Existing)
*   **Purpose:** Orchestrates ZRAM operations.
*   **Key Functions:**
    *   `set_writeback(device, backing_dev)`: Complex orchestration (Swapoff -> Reset -> Config -> Swapon).
    *   `persist_writeback(...)`: Writes to `zram-generator.conf`.

#### `core/hibernate_ctl.py` (**NEW**)
*   **Purpose:** Manages the persistent swap layer and low-level resume triggers.
*   **Key Functions:**
    *   `create_swapfile(path, size)`:
        *   **Pre-check:** Ensure sufficient free space (Size + 1GB buffer).
        *   **Ext4:** `fallocate -l [size] [path]`, `chmod 600`, `mkswap`.
        *   **Btrfs:**
            *   **Requirement:** Kernel 5.0+.
            *   Try: `btrfs filesystem mkswapfile --size [size] [path]` (Atomic & Correct).
            *   Fallback (Manual): `truncate -s 0`, `chattr +C`, `dd`, `chmod 600`, `mkswap`.
    *   `enable_swapon(path, priority=0)`: Activates swap with low priority.
    *   `get_resume_offset(path)`:
        *   **Swap Partition:** Offset is `0`.
        *   **Ext4:** Runs `filefrag -v`, parses physical offset of first extent.
        *   **Btrfs:** Runs `btrfs inspect-internal map-swapfile -r path`.
        *   **Other FS:** Return Error/Unsupported.
    *   `update_fstab(path, uuid)`: Appends entry to `/etc/fstab` (safe append, backup first).
    *   `trigger_resume_immediate(device_path, offset=0)`:
        *   **Low-level sysfs API** for immediate resume without reboot.
        *   Gets device major:minor from `os.stat(device_path).st_rdev`.
        *   Writes `major:minor` to `/sys/power/resume`.
        *   If offset > 0, writes to `/sys/power/resume_offset` first.
        *   Used for testing hibernation setup without reboot.
    *   `check_secure_boot()`: Reads `/sys/kernel/security/lockdown`. Returns warning if "confidentiality" is set.
    *   `detect_secure_boot_state()`:
        *   Checks `/sys/kernel/security/lockdown` for mode.
        *   Checks `/sys/firmware/efi/efivars/SecureBoot-*` for UEFI status.
        *   Returns: `'disabled'`, `'integrity'`, `'confidentiality'`.
    *   `can_hibernate_with_secure_boot()`: Returns `True` if lockdown mode allows hibernation (empty or integrity mode).

#### `core/boot_config.py` (Extended)
*   **Purpose:** Persistent kernel/boot settings and initramfs management.
*   **New Capabilities:**
    *   `read_current_cmdline()`: Parses `/proc/cmdline`.
    *   `update_grub_resume(uuid, offset)`:
        *   Edits `/etc/default/grub`.
        *   Updates `GRUB_CMDLINE_LINUX_DEFAULT` with `resume=UUID=... resume_offset=...`.
        *   Runs `update-grub`.
    *   `detect_initramfs_system()`: Returns `'initramfs-tools'`, `'mkinitcpio'`, or `'dracut'`.
        *   Detection logic: Check for `/etc/initramfs-tools/` (Ubuntu/Debian), `/etc/mkinitcpio.conf` (Arch), `/usr/bin/dracut` (Fedora).
    *   `configure_initramfs_resume(uuid, offset)`:
        *   **Ubuntu/Debian:** Creates `/etc/initramfs-tools/conf.d/resume` with:
            ```
            RESUME=UUID=...
            RESUME_OFFSET=...
            ```
        *   **Arch/Manjaro:** Validates `resume` hook is in `/etc/mkinitcpio.conf` HOOKS array (after `udev`, before `filesystems`).
        *   **Fedora:** Creates `/etc/dracut.conf.d/resume.conf` with `add_dracutmodules+=" resume "`.
    *   `regenerate_initramfs()`: Detects distro and runs:
        *   Ubuntu/Debian: `update-initramfs -u`
        *   Arch/Manjaro: `mkinitcpio -P`
        *   Fedora: `dracut -f --regenerate-all`

### 3.3 Functional Modules (The Skills)

#### `modules/sleep_config.py` (**NEW**)
*   **Purpose:** Configures systemd sleep behavior and hardware quirks.
*   **Key Functions:**
    *   `set_suspend_then_hibernate(delay_sec)`:
        *   Writes `/etc/systemd/sleep.conf.d/zman-hybrid.conf`.
        *   Sets `AllowSuspendThenHibernate=yes`, `HibernateDelaySec=...`.
    *   `set_image_size(size_bytes)`: Writes to `/sys/power/image_size`. 0 = smallest possible (slowest), Default = 2/5 RAM.
    *   `detect_rtc_quirk_needed()`:
        *   Checks DMI information for Framework laptops (Intel Core Ultra or AMD systems).
        *   Returns `True` if hardware is known to need RTC quirk.
    *   `check_rtc_alarm_status()`:
        *   Reads `/sys/module/rtc_cmos/parameters/use_acpi_alarm`.
        *   Returns `'Y'`, `'N'`, or `None` (if not available).
    *   `apply_rtc_quirk()`:
        *   **Runtime:** Writes `1` to `/sys/module/rtc_cmos/parameters/use_acpi_alarm`.
        *   **Persistent:** Adds kernel parameter `rtc_cmos.use_acpi_alarm=1` to GRUB config.
        *   **Critical:** Required for Framework 13 laptops (both Intel and AMD) to prevent suspend-then-hibernate from waking without hibernating.
    *   `verify_suspend_then_hibernate()`:
        *   After wakeup, checks `dmidecode -H1` Wake-up Type.
        *   If reports "Power Switch" instead of "APM Timer", RTC alarm failed.
        *   Suggests enabling RTC quirk.
    *   `set_lid_switch_action(action)`:
        *   Edit `/etc/systemd/logind.conf` (`HandleLidSwitch=suspend-then-hibernate`).

#### `modules/monitoring.py` (Existing)
*   **Purpose:** Live stats for UI.
*   **Key Functions:** `watch_device_usage`, `watch_system_stats`.

### 3.4 User Interface (The Face)

#### `ui/hibernate_page.py` (**NEW**)
*   **Role:** The main interface for enabling/managing hibernation.
*   **Components:**
    1.  **Header:** Readiness Status (e.g., "Hibernation Unavailable - No persistent swap").
    2.  **Swap Manager Card:**
        *   "Create Resume Storage" button. opens `DevicePickerDialog`.
        *   Logic:
            *   **Partition Selected:** If raw partition (Type 82), use directly. Format with `mkswap` if needed.
            *   **Filesystem Selected:** User picks Partition -> App suggests Swapfile size (RAM + 500MB) -> App creates file.
    3.  **Boot Configuration Card:**
        *   Shows current `resume` params.
        *   **LUKS Awareness:** If device is encrypted, must use the `UUID` of the *mapped* device (e.g., `/dev/mapper/luks-...`), NOT the raw physical partition.
        *   "Apply Boot Config" button (triggers `boot_config` + `initramfs` - **Root Required**).
    4.  **Power Policy Card:**
        *   Dropdown: "When Laptop Lid Closes" -> "Suspend", "Hibernate", "Suspend then Hibernate".
        *   Slider: "Hibernate after..." (15min to 4 hours).

---

## 4. Implementation Logic & Workflows

### Workflow A: Enabling Hibernation (The "Happy Path")
1.  **User Action:** User goes to "Hibernate" page, clicks "Setup Hibernate".
2.  **Select Storage:** User chooses `/dev/nvme0n1p2` (Root partition).
3.  **Safety Check:** `os_utils.check_device_safety` ensures it's a valid partition. `os_utils.get_fs_type` detects `ext4`.
4.  **Creation:**
    *   `hibernate_ctl.create_swapfile("/swapfile", size=32GB)` is called.
    *   Background worker shows progress spinner.
5.  **Activation:**
    *   `hibernate_ctl.enable_swapon("/swapfile", priority=0)`.
    *   `/etc/fstab` is updated.
6.  **Boot Config:**
    *   `UUID` fetched via `blkid`.
    *   `Offset` fetched via `filefrag`.
    *   `boot_config.update_grub_resume(UUID, Offset)`.
7.  **Finalize:**
    *   `update-initramfs` is run.
    *   User is prompted to **Reboot**.

### Workflow B: Handling Btrfs
1.  **Detection:** `os_utils.get_fs_type` detects `btrfs`.
2.  **Creation:** `hibernate_ctl` uses `truncate` + `chattr +C` BEFORE writing any data.
    *   *Note:* Fallback to specific Btrfs subvolume logic if necessary (often implies `/ @`).

---

## 5. Security & Safety Mechanisms (Verbose)

1.  **Data Loss Prevention (`os_utils`):**
    *   Before `dd` or `mkswap`, the target path is checked.
    *   If target is a block device, strict `blkid` check ensures no filesystem exists.
    *   If target is a file, ensures it doesn't overwrite critical system files (though specific paths like `/swapfile` are standard).

2.  **Secure Boot (`hibernate_ctl`):**
    *   On start, read `/sys/kernel/security/lockdown`.
    *   If mode is `confidentiality` or `integrity` (sometimes), hibernation may be blocked.
    *   **UI Behavior:** Show "Secure Boot Detected" warning banner. Suggest disabling Secure Boot if hibernation fails.

3.  **Atomic Config Writes:**
    *   All config file edits (`fstab`, `grub`, `systemd`) use `tempfile` -> `fsync` -> `rename` pattern to prevent corruption on crash.

4.  **Critical Implementation Details:**
    - **Offset Calculation (The "Map"):**
        - **Ext4:** Use `filefrag -v [swapfile]` (First physical offset).
        - **Btrfs:** CRITICAL. Cannot use `filefrag`. MUST use `btrfs inspect-internal map-swapfile -r [swapfile]`.
        - **Other:** Explicitly BLOCK XFS/ZFS/etc for now to ensure reliability.
    - **Kernel Parameters:**
        - `resume=UUID=[device_uuid]`
        - `resume_offset=[offset_value]`
    - **Tuning:**
        - `/sys/power/image_size`: Controls the target size of the image. Defaults to ~2/5 RAM. Can be written to `0` to request smallest possible size (slower) or larger values to speed up by avoiding compression/page release.
    - **Implementation:**
        - `hibernate_ctl.py` will handle filesystem detection and enforce Ext4/Btrfs paths.
    - [ ] Update `os_utils.py` (UUID/FS detection).

- [ ] **Phase 2: System Integration (`modules`)**
    - [ ] Implement `sleep_config.py` (Systemd interaction).
    - [ ] Verify `CMDLINE` parsing reliability.

- [ ] **Phase 3: UI Implementation (`ui`)**
    - [ ] Scaffold `hibernate_page.py`.
    - [ ] Connect `DevicePickerDialog` to Swapfile creation logic.
    - [ ] Build "Setup Wizard" flow with progress feedback.

- [ ] **Phase 4: Testing & Verification**
    - [ ] Test on Ext4 (Standard).
    - [ ] Test on Btrfs (NoCOW verification).
    - [ ] Verify Priority 100 (ZRAM) vs Priority 0 (Disk) behavior under load.

---

## 7. Reference Documentation (Data Sources)

This blueprint is derived from the comprehensive study of the following documentation files located in `devlopment/` and `devlopment/distro pages/`.

| File Path | Contribution to Blueprint |
| :--- | :--- |
| `a preview ready side project for zram managmet.md` | Defined the baseline architecture of Z-Manager and safety protocols for `os_utils`. |
| `Configuring Hibernation, Sleep, and ZRAM.md` | Established the core "Split-Horizon" strategy (Priorities 100 vs 0) and the requirement for separate persistent swap. |
| `bootparam(7).txt` | Source for `resume=` kernel parameter syntax used in `boot_config.py`. |
| `fstab(5).txt` | Guided the `pri=` implementation in `hibernate_ctl.py` for `/etc/fstab`. |
| `kernel-command-line(7).txt` | Confirmed `resume_offset` parameter availability for systemd generators. |
| `logind.conf(5).txt` | Defined `HandleLidSwitch` and `IdleAction` logic for `sleep_config.py`. |
| `systemd-hibernate-resume.service(8).txt` | Explained the low-level `/sys/power/resume` API used by `hibernate_ctl.py`. |
| `systemd-hibernate-resume@.service(8) .txt` | Clarified the templated service structure for resuming. |
| `systemd-hibernate-resume-generator(8).txt` | Confirmed how systemd parses kernel args to generate resume units. |
| `systemd-inhibit(1).txt` | Identified need to inhibit sleep during critical swap creation operations (future enhancement). |
| `distro pages/Power management Suspend and hibernate arch.txt` | **CRITICAL:** Provided the `btrfs inspect-internal` command for correct offset calculation on Btrfs. |
| `distro pages/systemd-hibernate.service.8.txt` | Cross-reference for systemd service behavior on different distros. |
| `distro pages/github.txt` | **CRITICAL:** Identified the `rtc_cmos` quirk for `suspend-then-hibernate` on specific hardware (Framework laptops). |
| `distro pages/ubuntu manpage.txt` | Confirmed Ubuntu-specific pathing for `sleep.conf.d`. |
| `distro pages/Basic sysfs Interfaces...txt` | Source for `/sys/power/image_size` tuning logic. |
| `distro pages/systemd-sleep.conf.5.txt` | Comprehensive reference for `HibernateDelaySec` and `AllowSuspendThenHibernate`. |
| `distro pages/systemd-sleep.8.en.txt` | Detailed the hook system for `systemd-sleep` (context, not directly implemented). |
| `distro pages/swapsapce.txt` | Validated `vm.swappiness` and `vm.vfs_cache_pressure` tuning values for the `tune_page`. |
