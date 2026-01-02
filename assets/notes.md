# Project Notes & Ideas

## 🛡️ Live Writeback & Safety

### The Challenge

Changing the `writeback_device` on a live ZRAM device requires resetting it.

1. `swapoff /dev/zram0` (Evacuates data back to RAM).
2. `echo 1 > /sys/block/zram0/reset` (Clears configuration).
3. Reconfigure with new writeback device.
4. `mkswap` & `swapon`.

### Safety Constraints (Feasibility Check)

* **RAM Availability:** Before `swapoff`, we MUST check if `Currently Used Swap < Available RAM`.
  * *If RAM is full:* `swapoff` will trigger OOM Killer or freeze the system.
  * *Action:* The backend must explicitly block this operation if unsafe.
* **The "TTY" Idea:** The user suggested "implement going into TTY".
  * *Constraint:* A GUI app cannot programmatically "force" the session into a TTY (Ctrl+Alt+F3).
  * *Alternative:* We can show a **Critical Warning Dialog**: "This operation moves X GB of data to RAM. Your screen may freeze for 10-30 seconds. Do not force reboot."
* **Filesystem Safety:**
  * We already have `check_device_safety()` (blkid) in `core/os_utils.py` to prevent overwriting `ext4`/`ntfs` partitions. This is good.

## 🧠 Tuning Parameters Explained

### 1. `vm.page-cluster`

* **What is it?** Controls "readahead" for swap.
  * Default `3`: Reads $2^3 = 8$ pages (32KB) at a time. Good for spinning hard drives (reduces seek time).
* **For ZRAM:** Should be `0` ($2^0 = 1$ page).
  * *Why?* ZRAM is CPU-bound, not seek-bound. Reading 8 pages when you only need 1 is a waste of CPU cycles (decompression overhead).
  * *Verdict:* **Keep.** This is highly relevant to ZRAM performance.

### 2. `vm.vfs_cache_pressure`

* **What is it?** Controls how aggressively the kernel reclaims "inode/dentry" cache (filesystem structure) vs "page cache" (file contents).
  * Default `100`: "Fair" balance.
  * `>100`: Reclaims directory structure memory faster.
* **Relevance:** Marginal. It helps on extremely low-RAM systems to prevent "directory listing" memory from eating up space that applications need.
  * *Verdict:* **Optional.** It's not strictly ZRAM-related, but it is "Memory Management" related.

### 3. I/O Scheduler

* **Scope:** Applies to the **entire physical disk** (e.g., `/dev/nvme0n1`), not just the partition.
* **Conflict:** Setting this for ZRAM affects the OS, Games, and Browser performance.
* **Verdict:** **Remove from UI.** Too invasive.

## 💤 Hibernation Support (The "Sleep" Problem)

### The Conflict

* **ZRAM is RAM:** You cannot hibernate *to* ZRAM, because ZRAM allows the power to be cut, erasing the data.
* **The Resume Loop:** If the kernel tries to hibernate to ZRAM, it will fail.
* **Priority Issue:** ZRAM usually has higher priority (e.g., 100) than Disk Swap (-2). The kernel fills high-priority swap first. If ZRAM is full, hibernation *might* spill over to Disk Swap correctly, but it's risky.

### "Robust" Implementation Idea

We need a **systemd-sleep hook** script (`/lib/systemd/system-sleep/zman-hibernate`).

* **On Hibernate (Pre):** `swapoff /dev/zram0`.
  * *Why:* Forces all data out of ZRAM. Since we are hibernating, we *must* write everything to the physical Disk Swap anyway. This ensures the ZRAM device is empty and out of the way.
* **On Resume (Post):** `swapon /dev/zram0`.
  * *Result:* Computer wakes up, ZRAM comes back online empty and ready for fresh hot pages.

### Constraint

* Requires `root` to install the script.
* Requires a **Physical Swap Device** (Partition or File) that is $\ge$ Total RAM. Z-Manager cannot manufacture this space if it doesn't exist.

✦ The current parser and writer (configparser) are functional but have a few limitations when dealing with system configuration files that humans might also edit manually. Here
  are the key improvements that could be made:

1. Preserve Comments and Formatting (The Biggest Issue)
   
   * Current State: Python's standard configparser strips all comments (# this is a comment) and re-orders/re-formats the file when it writes it back.
   * The Problem: If a user manually adds notes like # Optimized for gaming or # Don't touch this, the app will delete them as soon as it saves any change.
   * Improvement: Switch to a library like `ConfigObj` or write a custom "round-trip" parser. This would allow the app to read the file, modify just one value (e.g., change size
     from 4G to 8G), and save it back while keeping all user comments and whitespace exactly as they were.

2. Validation of Values
   
   * Current State: The writer will happily write zram-size = banana if the code tells it to. The validation happens only when systemd tries to start the service and fails.
   * Improvement: Add a validation layer in the writer before saving.
     * Regex Check: Ensure zram-size matches patterns like min(...), ram, or \d+[MG].
     * Algorithm Check: Verify the algorithm is one supported by /proc/crypto (e.g., prevent writing compression-algorithm = lz5 if the kernel doesn't support it).

3. Support for "Global" or [zram-generator] Sections
   
   * Current State: The app assumes every section is a device (e.g., [zram0]).
   * The Gap: Newer versions of zram-generator might introduce a global [zram-generator] section for system-wide defaults. The current logic might try to treat [zram-generator]
     as a device named "zram-generator", which would be incorrect.
   * Improvement: Explicitly handle and separate "device sections" from "global config sections" to allow for more advanced configurations.

4. Backup Mechanism
   
   * Current State: The "atomic write" prevents corruption, but it overwrites the previous valid configuration.
   * Improvement: Before writing, automatically copy the current file to .bak (e.g., zram-generator.conf.bak). This gives the user a manual recovery option if they regret their
     changes.

5. Diff-Based Writing
   
   * Current State: The app rewrites the entire file every time.
   * Improvement: Only touch the file if the content actually changes. (The current app does check for changes in memory, but a diff-based write is even safer).
   
   Which of these sounds most valuable to you? I can help implement the "Backup" or "Validation" improvements fairly easily. The "Preserve Comments" is harder but makes the app
   much more "polite" to power users.

✦ The current parser and writer (configparser) are functional but have a few limitations when dealing with system configuration files that humans might also edit manually. Here
  are the key improvements that could be made:

1. Preserve Comments and Formatting (The Biggest Issue)
   
   * Current State: Python's standard configparser strips all comments (# this is a comment) and re-orders/re-formats the file when it writes it back.
   * The Problem: If a user manually adds notes like # Optimized for gaming or # Don't touch this, the app will delete them as soon as it saves any change.
   * Improvement: Switch to a library like `ConfigObj` or write a custom "round-trip" parser. This would allow the app to read the file, modify just one value (e.g., change size
     from 4G to 8G), and save it back while keeping all user comments and whitespace exactly as they were.

2. Validation of Values
   
   * Current State: The writer will happily write zram-size = banana if the code tells it to. The validation happens only when systemd tries to start the service and fails.
   * Improvement: Add a validation layer in the writer before saving.
     * Regex Check: Ensure zram-size matches patterns like min(...), ram, or \d+[MG].
     * Algorithm Check: Verify the algorithm is one supported by /proc/crypto (e.g., prevent writing compression-algorithm = lz5 if the kernel doesn't support it).

3. Support for "Global" or [zram-generator] Sections
   
   * Current State: The app assumes every section is a device (e.g., [zram0]).
   * The Gap: Newer versions of zram-generator might introduce a global [zram-generator] section for system-wide defaults. The current logic might try to treat [zram-generator]
     as a device named "zram-generator", which would be incorrect.
   * Improvement: Explicitly handle and separate "device sections" from "global config sections" to allow for more advanced configurations.

4. Backup Mechanism
   
   * Current State: The "atomic write" prevents corruption, but it overwrites the previous valid configuration.
   * Improvement: Before writing, automatically copy the current file to .bak (e.g., zram-generator.conf.bak). This gives the user a manual recovery option if they regret their
     changes.

5. Diff-Based Writing
   
   * Current State: The app rewrites the entire file every time.
   * Improvement: Only touch the file if the content actually changes. (The current app does check for changes in memory, but a diff-based write is even safer).
   
   Which of these sounds most valuable to you? I can help implement the "Backup" or "Validation" improvements fairly easily. The "Preserve Comments" is harder but makes the app
   much more "polite" to power users.
