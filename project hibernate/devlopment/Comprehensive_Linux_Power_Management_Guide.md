# Comprehensive Linux Power Management & Memory Architecture Guide

This document serves as a "Source of Truth" regarding Linux power management states, their hardware implications, and how they interact with complex memory setups like ZRAM and Swap.

---

## Part 1: The Spectrum of Power Management (Kernel & Systemd)

Linux offers a hierarchy of power states, ranging from pure software pausing to complete electrical shutdown. While ACPI defines standard hardware states (S0-S5), Linux and Systemd combine these into highly configurable strategies.

### The "Active" Sleep States (Kernel Supported)

#### 1. Suspend-to-Idle (S2Idle / Freeze / S0ix)
*   **Kernel Mode:** `freeze`
*   **Hardware State:** CPU remains powered but idle. "Freeze" is purely software-based (pausing processes).
*   **Behavior:** The system stops user-space software. Hardware stays on but enters low-power modes.
*   **Resume Speed:** Instant (< 1 second).
*   **Usage Status:** **Standard on modern laptops** (Ultrabooks, Intel & AMD mobile chips). It is often the default fallback if deeper sleep is unsupported.
*   **Power Usage:** High relative to other sleep modes (battery drains in days).
*   **Note:** Often called "S0ix" on Intel hardware.

#### 2. Standby (S1 / Shallow)
*   **Kernel Mode:** `standby`
*   **Hardware State:** CPU clock is stopped, but CPU retains power. Peripherals may be powered down.
*   **Behavior:** A step deeper than idle but shallower than full suspend.
*   **Resume Speed:** Very Fast (1-2 seconds).
*   **Usage Status:** **Legacy / Rare**. Most modern hardware executes S2Idle or S3 instead.
*   **Power Usage:** Moderate.

#### 3. Suspend-to-RAM (S3 / Deep / Mem)
*   **Kernel Mode:** `mem`
*   **Hardware State:** **Power is cut** to the CPU, GPU, and Disk. **Power remains ON for RAM** (in Self-Refresh mode).
*   **Behavior:** The OS context is preserved purely in the RAM chips. If the battery dies, data is lost.
*   **Resume Speed:** Fast (2-5 seconds).
*   **Usage Status:** **The Standard** for most desktops and older laptops.
*   **Power Usage:** Very Low (battery lasts weeks).

#### 4. Hibernation (S4 / Disk)
*   **Kernel Mode:** `disk`
*   **Hardware State:** **Zero Power** (Mechanical Off).
*   **Behavior:** The contents of RAM are written to Non-Volatile Storage (Hard Drive/SSD Swap). The system shuts down completely.
*   **Resume Speed:** Slow (depends on disk speed & RAM size; 10-30 seconds). Requires a full BIOS boot sequence + Kernel load.
*   **Usage Status:** **Active but Complex**. Used when preservation of state is critical over long periods or power loss is expected.
*   **Power Usage:** Zero.

### The "Composite" Strategies (Systemd Orchestrated)

These are not single hardware states but intelligent combinations managed by systemd.

#### 5. Hybrid Sleep (Suspend-to-Both)
*   **Mechanism:** Combines **S3 (RAM)** + **S4 (Disk)**.
*   **Behavior:** It writes the RAM contents to Disk (like Hibernation) **BUT** does not turn off. It then enters Suspend-to-RAM (S3).
    *   **Scenario A (Normal):** You wake the PC. It wakes from RAM (Fast).
    *   **Scenario B (Battery dies):** RAM loses power. You turn on the PC. It detects the dirty swap image and resumes from Disk (Saved!).
*   **Usage Status:** **Recommended for highly reliable setups**.

#### 6. Suspend-then-Hibernate
*   **Mechanism:** Transitions from **S3 (RAM)** -> **S4 (Disk)** after a delay.
*   **Behavior:**
    1. System enters Suspend-to-RAM (S3).
    2. A Real-Time Clock (RTC) alarm is set for a specific duration (e.g., 2 hours).
    3. **Wake-up:** After 2 hours (or if battery is critical), the system wakes partially.
    4. **Transition:** It writes RAM to Disk (Hibernate) and powers off completely.
*   **Usage Status:** **Ideal for Laptops**. Balances instant wake convenience with long-term battery saving.

### The "Shutdown" & "Transition" States

Often forgotten, these are valid power management targets.

#### 7. Power Off (S5 / Soft Off)
*   **Action:** `poweroff`
*   **Hardware State:** System is mechanically off, but PSU may supply +5VSB (Standby power) for wake-on-LAN or power button/keyboard wake events.
*   **Behavior:** Clean shutdown of all services and unmounting of filesystems.

#### 8. Halt
*   **Action:** `halt`
*   **Hardware State:** CPU stops executing instructions. Power **remains ON**.
*   **Behavior:** The OS stops, but the system does not power down.
*   **Usage Status:** Rare. Mostly used for low-level maintenance or hardware that cannot power itself off.

#### 9. Kexec (Fast Reboot)
*   **Action:** `kexec`
*   **Behavior:** A "Soft Reboot". The current kernel loads the *new* kernel directly into memory and jumps to it.
*   **Difference:** It **skips** the Bios/UEFI hardware initialization (POST), making reboots extremely fast.
*   **Usage Status:** Useful for servers or rapid development cycles.

---

## Part 2: The Memory Relationship (ZRAM vs. Suspend vs. Hibernate)

There is often confusion about how ZRAM (Compressed RAM) interacts with power states.

### 1. ZRAM and Suspend-to-RAM (S3)
**Compatibility:** 100% Compatible.
**Why?**
*   **ZRAM is just data:** ZRAM is a virtual block device that lives *inside* your physical RAM sticks.
*   **S3 keeps RAM alive:** When you Suspend-to-RAM, the motherboard keeps voltage flowing to the RAM sticks to preserve their ones and zeros.
*   **Result:** Since ZRAM is just "ones and zeros in RAM," it is preserved automatically. When you wake up, the CPU accesses the RAM, finds the compressed ZRAM data exacty where it left it. **No action is required.**

### 2. ZRAM and Hibernation (S4)
**Compatibility:** **INCOMPATIBLE** (Directly).
**Why?**
*   **Hibernation kills power:** RAM loses power. ZRAM (being inside RAM) vanishes.
*   **The "Resume" problem:** To Hibernate, you must save the *state* of the system to a persistent disk. You cannot save "Compressed RAM" into "Swap on Disk" easily because the kernel needs to reconstruct the *original* memory map.
*   **The Mechanism:**
    1. When Hibernation starts, the Kernel "thaws" processes.
    2. It realizes it needs to free up enough RAM to create the snapshot image.
    3. Any data in ZRAM must be **decompressed** and potentially moved to the **Disk-based Swap** (because ZRAM is about to vanish).
    4. The image is written to the persistent Disk Swap.

### 3. The "Split-Horizon" Coexistence Strategy
To make ZRAM and Hibernation live in harmony, we use **Swap Priorities** (`/etc/fstab` or systemd units).

| Device | Priority | Purpose |
| :--- | :--- | :--- |
| **ZRAM** | **100 (High)** | Catches all normal runtime overflow. Compresses data. Speeds up system. |
| **Disk Swap** | **0 (Low)** | Stays empty 99% of the time. Used only if ZRAM fills up OR for Hibernation storage. |

**The Workflow:**
1.  **Usage:** User opens 50 Chrome Tabs. System uses ZRAM (Priority 100). Disk Swap is empty.
2.  **Hibernate Triggered:** System prepares to power off.
3.  **The Shift:** The Kernel knows it needs to save state. It looks for a `resume=` partition/file on the disk (ignoring ZRAM).
4.  **The Write:** It dumps the contents of RAM (active apps + decompressed data) into the Disk Swap partition designated for resume.
5.  **Power Off.**

**Conclusion for Z-Manager:**
You are building the **Suspend-then-Hibernate** workflow using the **Split-Horizon** strategy. This gives the user the performance of ZRAM while awake/sleeping, and the safety of Disk persistence when hibernating.

---

## Part 3: Recommended Strategies with ZRAM

Since you asked about the "Go-To" strategy for different form factors, here is the breakdown:

### 1. For Desktops (PCs) -> Hybrid Sleep
*   **The Strategy:** `Hybrid Sleep` (Suspend-to-Both).
*   **Why?** Desktops are usually plugged in, so battery drain isn't an issue.
*   **Benefit:**
    *   **Speed:** Wakes instantly from RAM (S3) just like a normal sleep.
    *   **Safety:** If a power outage occurs (or you unplug it to move it), the "Backup" image on disk takes over.
    *   **ZRAM Interaction:** ZRAM stays alive in the RAM portion. If power is cut, the ZRAM data is lost, BUT the system resumes from the Disk image (where the kernel pre-saved the RAM contents).

### 2. For Laptops -> Suspend-then-Hibernate
*   **The Strategy:** `Suspend-then-Hibernate`.
*   **Why?** Batteries drain even in sleep mode (S3 consumes ~1-5% per hour).
*   **Benefit:**
    *   **Short Term:** Lid close = Instant Sleep (S3). Fast resume if you open it soon.
    *   **Long Term:** After X hours, it wakes up and Hibernates (S4). You can leave it in a bag for weeks and it won't die.
    *   **ZRAM Interaction:** ZRAM provides extra memory while working and sleeping. When the transition to Hibernate happens, the kernel safely writes everything to disk and turns off.
