# 🏛️ systemd Delegation Roadmap: The "Orchestrator" Pivot

**Status:** Technical Design Phase  
**Objective:** Replace fragile, manual Python "heavy-lifting" with native systemd infrastructure to improve robustness, reduce code-surface, and eliminate "Legacy Debt."

---

## 1. Configuration: The "Hierarchy of Truth"
**Current State (`core/config.py`):** Manual crawling of `/etc`, `/run`, and `/usr/lib`. Blind to `.d` drop-in directories. "First-one-wins" logic.

### ⚠️ Critical Flaws Addressed:
*   **State Desync:** Current code only sees ~20% of possible config locations, leading to "Ghost Settings" (vendor defaults the app can't see).
*   **Newline Injection:** Current validation is "loose." Hardening is required to prevent malformed config strings from breaking section boundaries.
*   **Manual Merging:** Avoiding 100+ lines of custom Python logic to replicate systemd's complex file-priority rules.

### 🎯 The Delegation Path: `systemd-analyze cat-config`
*   **Command:** `systemd-analyze cat-config systemd/zram-generator.conf`
*   **Logic:** Feed the merged stdout stream directly to `ConfigObj(list_values=False)`.
*   **Benefit:** Zero Logic Gap (Matches kernel's exact view); Handles "Masked" files automatically.

---

## 2. Hibernation: "Readiness & Safety"
**Current State (`core/hibernate_ctl.py`):** Manual scraping of `/proc/meminfo` and `/sys/kernel/security/lockdown`.

### ⚠️ Critical Flaws Addressed:
*   **Secure Boot Lockdown:** Current code can't reliably predict if the kernel will block hibernation at the last second due to policy.
*   **GPU/Inhibitor Blindness:** Manual checks miss hardware-level reasons why hibernation might fail (e.g., specific driver incompatibilities).
*   **ZRAM-Hibernation Paradox:** Missing logic to calculate the "Expansion Factor" (Ensuring Swap >= RAM + ZRAM compressed data).

### 🎯 The Delegation Path: `systemd-logind` D-Bus
*   **Method:** `org.freedesktop.login1.Manager.CanHibernate`
*   **Logic:** Use D-Bus to get a "System-Verified" yes/no/na status.
*   **Benefit:** Checks Secure Boot, Drivers, and Active Inhibitors (like media playback) in one call.

---

## 3. Persistence: The "fstab Exit" (Deprecation of `update_fstab`)
**Current State (`core/hibernate_ctl.py`):** Manual string-appending to `/etc/fstab`.

### ⚠️ Critical Flaws Addressed:
*   **Global State Risk:** A single typo in `fstab` can cause a "Kernel Panic" or "Emergency Mode" at boot.
*   **Race Conditions:** Multiple app instances or manual edits can lead to duplicate entries and 90-second boot timeouts.
*   **The "Regex Nightmare":** Cleaning up `fstab` entries requires fragile text-scraping.

### 🎯 The Delegation Path: Native `.swap` Units
*   **Unit Format:** `/etc/systemd/system/var-swapfile.swap`
*   **Implementation:** Generate a simple INI-style unit; use `atomic_write_to_file`.
*   **Benefit:** **Atomic Cleanup** (Delete file = Entry gone); Isolation (Errors in our unit cannot break the system boot).

---

## 4. Hardware/FS Logic: "Physical Offsets"
**Current State (`core/hibernate_ctl.py`):** "Scraping" text from `filefrag -v` and `blkid`.

### ⚠️ Critical Flaws Addressed:
*   **Fragile Scrapers:** If `e2fsprogs` updates and changes the `filefrag` output format by one space, hibernation resume fails.
*   **Filesystem Minefield:** Manual logic for Btrfs vs Ext4 vs XFS is complex and prone to "Extents" errors. (ZFS/LUKS/LVM awareness is currently missing).

### 🎯 The Delegation Path: `systemd-tmpfiles` & FS-Specific Tooling
*   **Logic:** Use `systemd-tmpfiles` for safe "NoCOW" file creation. Use `btrfs inspect-internal` for Btrfs offsets instead of generic scrapers.
*   **Benefit:** Offloads the "Magic Attributes" (NoCOW, Permissions 0600) to the OS standard tools.

---

## 5. Summary of Next Steps
1.  **Refactor `core/config.py`**: Transition to `systemd-analyze cat-config`.
2.  **Modernize `core/hibernate_ctl.py`**: 
    *   Implement D-Bus `CanHibernate` check.
    *   Build the `.swap` unit generator.
    *   Mark `update_fstab` as **Deprecated**.
3.  **Harden Validation**: Add newline/injection protection to `config_writer.py`.
