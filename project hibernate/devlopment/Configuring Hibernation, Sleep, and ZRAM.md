# **Unified Power Management and Hierarchical Memory Architecture: A Comprehensive Implementation Guide for ZRAM, Suspend-to-RAM, and Hibernation in Linux Systems**

## **1\. Executive Summary**

In the contemporary landscape of Linux systems engineering, the management of volatile memory (RAM) and non-volatile storage presents a complex optimization challenge. As applications demand increasing amounts of memory and hardware form factors shift toward mobile and embedded architectures, the traditional boundaries between active memory and storage have blurred. The introduction of Compressed RAM (ZRAM) technologies has revolutionized memory efficiency, offering a mechanism to significantly extend effective capacity and reduce I/O latency by storing swapped pages in compressed formats within the physical RAM itself.  
However, the integration of ZRAM introduces a fundamental architectural conflict with Advanced Configuration and Power Interface (ACPI) state S4, commonly known as hibernation. Because ZRAM is an emulated block device residing entirely within volatile memory, it cannot retain data upon the cessation of power. Consequently, a system configured exclusively with ZRAM for swap lacks the persistent backing store required to save the kernel's memory snapshot during hibernation, rendering the feature inoperable.  
This research report provides an exhaustive technical analysis and implementation guide for resolving this conflict. It details the construction of a "Split-Horizon" memory architecture that leverages systemd-zram-generator for high-performance, high-priority runtime swapping, while simultaneously maintaining a secondary, low-priority persistent swap substrate (file or partition) dedicated to hibernation.  
Through a rigorous examination of kernel parameters, systemd unit logic, filesystem constraints (specifically within Btrfs and Ext4 environments), and bootloader configurations, this document demonstrates how to orchestrate a seamless suspend-then-hibernate workflow. This workflow utilizes ZRAM for immediate responsiveness and battery preservation during short idle periods (S3 Suspend-to-RAM) and automatically transitions to persistent disk storage for long-term power preservation (S4 Hibernation), effectively unifying speed, efficiency, and state persistence.

## **2\. Theoretical Framework: The Memory-Power Nexus**

To accurately implement a robust hybrid power management strategy, it is essential to first deconstruct the underlying theoretical mechanisms of Linux memory management and the ACPI power states that govern system behavior. The interaction between the kernel's Page Frame Replacement Algorithm (PFRA) and the hardware's power states defines the constraints and opportunities of this architecture.

### **2.1 The Evolution of Linux Swap**

Historically, swap space was conceived as a rudimentary extension of physical RAM—a slow, disk-based overflow reservoir used when physical memory was exhausted. In modern kernels, however, swap plays a far more nuanced and proactive role. It serves as a mechanism for anonymous page reclamation, allowing the kernel to evict rarely accessed data (heap and stack memory) to persistent storage, thereby freeing up valuable physical RAM for the page cache (file-backed memory). This behavior directly improves system responsiveness by keeping frequently used executables and libraries in fast memory.1

#### **2.1.1 ZRAM: The Volatility Paradigm**

ZRAM fundamentally alters this hierarchy by inserting a compressed block device between the main memory and the disk. When the kernel swaps a page to a ZRAM device, the data is not written to a slow SSD or HDD; instead, it is compressed (using algorithms like LZO, LZ4, or ZSTD) and stored in a dynamically allocated portion of the physical RAM.2  
The performance implications are profound. While a typical NVMe SSD might offer write latencies in the range of 20-100 microseconds, ZRAM operations occur at near-RAM speeds, primarily bottlenecked only by CPU compression cycles. This results in a system that performs significantly better under memory pressure. However, the trade-off is volatility. A ZRAM device is a virtual construct; its contents exist only as long as the RAM modules are powered. This physical reality makes ZRAM inherently incompatible with hibernation, which by definition involves the total removal of power from the system.3

### **2.2 ACPI Sleep States and Kernel Support**

The Advanced Configuration and Power Interface (ACPI) specification defines global system states that dictate power consumption and wake-up latency.

* **S0 (Working):** The system is fully powered.  
* **S3 (Suspend-to-RAM):** Context is saved to RAM. The CPU, disk, and peripherals are powered down, but the RAM remains energized to retain data. Resume is near-instantaneous. ZRAM persists in this state because the RAM is powered.5  
* **S4 (Hibernation/Suspend-to-Disk):** The system context is saved to non-volatile storage (disk). The hardware is completely powered off (mechanical off). Upon reboot, the kernel loads the saved image from the disk into RAM. ZRAM **cannot** persist in this state.6

#### **2.2.1 The Hybrid Compromise: Suspend-then-Hibernate**

The integration of these states is managed by systemd through a mode known as suspend-then-hibernate. This mode attempts to bridge the gap between the speed of S3 and the power savings of S4. The system initially enters S3, keeping data in RAM (and thus ZRAM). A Real-Time Clock (RTC) alarm is set for a specific interval (e.g., 2 hours). If the user does not resume the system before the timer expires, the system wakes briefly, writes the memory image to persistent storage, and then enters S4.5  
This mode is the target state for our architecture: utilizing ZRAM for the S3 phase and a disk-backed swap for the eventual transition to S4.

## **3\. High-Performance Runtime Swap: Implementing ZRAM**

The first pillar of the architecture is establishing the high-performance volatile swap layer. We utilize systemd-zram-generator, a modern tool that integrates with the systemd boot process to dynamically configure ZRAM devices based on available system resources.

### **3.1 The systemd-zram-generator Mechanism**

Unlike static initialization scripts, systemd-zram-generator acts as a systemd generator binary. During the early boot phase (before unit files are loaded), it reads configuration files and generates native systemd service units (systemd-zram-setup@zramN.service) on the fly. This ensures that ZRAM devices are initialized early in the userspace initialization, making them available before heavy applications launch.8

### **3.2 Configuration Strategy**

The configuration is typically located at /etc/systemd/zram-generator.conf. To achieve the dual goals of maximizing runtime performance and allowing for hibernation fallback, we must configure specific parameters: compression algorithms, device sizing, and, most critically, swap priority.

#### **3.2.1 Prioritization Logic**

Linux manages multiple swap devices using a priority tiering system. The kernel pages memory out to the highest priority device first. Only when that device is full does it cascade to the next priority tier.  
For our architecture, ZRAM must be the primary target. We assign it a high priority (e.g., 100), while the persistent hibernation swap is assigned a low priority (e.g., 0). This ensures that during normal operation, the system utilizes the fast, compressed ZRAM device exclusively. The slower disk swap remains empty, reducing wear on the SSD and preserving I/O bandwidth, essentially sitting idle until the hibernation trigger is invoked.2

#### **3.2.2 Compression Algorithms: The Case for Zstd**

The choice of compression algorithm dictates the balance between CPU usage and effective memory density. systemd-zram-generator supports various algorithms exposed by the kernel crypto API.

* **LZO-RLE:** Extremely fast compression/decompression, but lower compression ratios. Often the kernel default.  
* **LZ4:** Balanced, very fast decompression.  
* **ZSTD (Zstandard):** Offers superior compression ratios with acceptable CPU overhead. In a memory-constrained environment, ZSTD is often preferred as it allows more pages to be stored in the ZRAM device, effectively "creating" more RAM.2

### **3.3 Implementation Details**

The recommended configuration file /etc/systemd/zram-generator.conf is constructed as follows:

Ini, TOML

\# /etc/systemd/zram-generator.conf

\[zram0\]  
\# Allocate 50% of total RAM, capped at 8GB, to prevent  
\# memory starvation for uncompressible operational data.  
zram-size \= min(ram / 2, 8192\)

\# Use ZSTD for optimal compression ratio.  
compression-algorithm \= zstd

\# CRITICAL: High priority ensures this is used before disk swap.  
swap-priority \= 100

\# Format as swap immediately.  
fs-type \= swap

**Insights on Sizing:** The directive zram-size \= min(ram / 2, 8192\) creates a device whose *uncompressed* capacity is half of physical RAM. It is a misconception that ZRAM "uses" this RAM immediately. ZRAM dynamically allocates memory blocks only as data is written to it. A 4GB ZRAM device containing no data consumes near-zero physical RAM.2

### **3.4 The Misunderstanding of writeback-device**

The zram-generator includes an option called writeback-device. It is vital to clarify that **this is not a hibernation mechanism**. The writeback feature allows the ZRAM controller to eject incompressible or idle pages to a backing block device *while the system is running* to prevent the ZRAM device from filling up with data that achieves poor compression ratios.11  
While one could theoretically use the hibernation partition as a writeback device, this conflates two distinct functions (runtime memory tiering vs. power state persistence). For stability and clarity, it is recommended to keep the ZRAM device pure and utilize the disk swap solely as an independent entity managed by the kernel's hibernation logic.13

## **4\. The Persistence Layer: Configuring Disk-Based Swap**

Since ZRAM cannot sustain data across a power cycle, a secondary, persistent swap medium is mandatory for hibernation. This layer acts as the "safety net" where the RAM contents are serialized and stored before the system cuts power.

### **4.1 Partition vs. Swap File**

Traditionally, a dedicated swap partition was required. However, modern kernels and filesystems support swap files with equal performance, offering greater flexibility in resizing. The choice often depends on the filesystem in use.  
**Comparison of Persistent Storage Options:**

| Feature | Swap Partition | Swap File (Ext4) | Swap File (Btrfs) |
| :---- | :---- | :---- | :---- |
| **Resizability** | Difficult (Requires re-partitioning) | Easy (dd / fallocate) | Easy (with constraints) |
| **Hibernation Support** | Native | Supported (Requires Offset) | Supported (Requires Offset \+ NoCOW) |
| **Complexity** | Low | Low | High |
| **Snapshot Exclusion** | N/A (Outside FS) | Automatic | Manual Config Required |

### **4.2 Sizing the Hibernation Store**

The persistent swap must be large enough to hold the active memory image. While the kernel compresses the image (targeting \~40% of RAM by default via /sys/power/image\_size), relying on this compression is risky. If the active working set of memory is incompressible (e.g., encrypted data, already compressed media) and exceeds the swap size, hibernation will fail critically at runtime.9  
**Recommendation:** Provision the swap file/partition to be equal to the size of physical RAM \+ a safety buffer (e.g., 100-200MB) or RAM \+ ZRAM size if absolute safety is required, though RAM \* 1.0 is generally sufficient for 99% of use cases.9

### **4.3 Filesystem-Specific Implementation**

#### **4.3.1 Scenario A: Ext4 / XFS (Standard)**

On standard filesystems like Ext4, creating a swap file is straightforward. However, the use of fallocate is sometimes discouraged for hibernation files because it may create "holes" (discontinuous blocks) that the kernel's resume code cannot handle. dd is the most robust method.

Bash

\# Create a 16GB swap file filled with zeros (ensures allocation)  
sudo dd if=/dev/zero of=/swapfile bs=1G count=16 status=progress

\# Set strict permissions (root read/write only)  
sudo chmod 600 /swapfile

\# Format as swap  
sudo mkswap /swapfile

#### **4.3.2 Scenario B: Btrfs (Advanced)**

Btrfs presents significant challenges due to its Copy-on-Write (CoW) nature. If a swap file is subjected to CoW, its physical location on the disk changes, invalidating the kernel's resume offset mapping.  
**Requirements for Btrfs:**

1. **NoCOW Attribute:** The file must have the \+C attribute set immediately upon creation (empty state) to disable CoW.  
2. **No Compression:** Compression must be disabled for the file.  
3. **No Snapshots:** The file cannot be part of a snapshot operation in a way that creates inconsistency.9

**Btrfs Implementation Steps:**

Bash

\# Create an empty file  
sudo truncate \-s 0 /swapfile

\# Disable CoW  
sudo chattr \+C /swapfile

\# Allocate space (Btrfs specific tool preferred for preallocation)  
sudo btrfs filesystem mkswapfile \--size 16G /swapfile

\# Enable swap  
sudo swapon /swapfile

### **4.4 Tiered Activation in /etc/fstab**

To integrate this new persistent device into the hierarchy established in Section 3, we edit /etc/fstab. We must assign a priority significantly *lower* than the ZRAM device (which was 100).

Code snippet

\# /etc/fstab

\# The persistent swap file.  
\# Priority set to 0 to ensure it is only used if ZRAM (prio 100\) overflows,  
\# or specifically demanded by the hibernation process.  
/swapfile   none    swap    defaults,pri=0   0 0

With this configuration, the system possesses two swap devices:

1. /dev/zram0 (Priority 100): Used for all active swapping.  
2. /swapfile (Priority 0): Idle reserve, ready for hibernation image storage.9

## **5\. Kernel Resume Mechanics: Bridging Boot and State Restoration**

Configuring the storage is only half the battle. The Linux kernel, upon a cold boot, is unaware that a hibernation image exists in a file on the disk. We must explicitly instruct the kernel via bootloader parameters to look for this image.

### **5.1 The resume and resume\_offset Parameters**

When hibernating to a partition, the kernel only needs the device path (e.g., resume=/dev/sda2 or resume=UUID=...). However, when hibernating to a **swap file**, the kernel cannot mount the filesystem to find the file because resuming happens *before* filesystems are mounted.  
Therefore, we must provide the kernel with:

1. **The Device:** The partition holding the swap file (resume=UUID=...).  
2. **The Physical Offset:** The exact physical block number on that partition where the swap file header begins (resume\_offset=...).18

### **5.2 Calculating the Physical Offset**

The tool filefrag reports the physical block mapping of a file. We need the physical offset of the first extent.  
**Command for Extraction:**

Bash

sudo filefrag \-v /swapfile

The output will look like this:  
File size of /swapfile is 17179869184 (4194304 blocks of 4096 bytes)  
ext: logical\_offset: physical\_offset: length: expected: flags:  
0: 0.. 0: 34816.. 34816: 1:  
1: 1.. 30719: 34817.. 65535: 30719: unwritten  
...  
The value we need is the first physical\_offset (e.g., 34816). Note that filefrag often outputs two dots .. which must be stripped.  
Automated Extraction Command:  
For automation scripts or precise extraction, awk is used to filter the output:

Bash

sudo filefrag \-v /swapfile | awk '{ if($1=="0:"){print substr($4, 1, length($4)-2)} }'

This command isolates the block number of extent 0\.16  
Warning for Btrfs:  
On Btrfs, standard filefrag may report virtual offsets depending on the kernel version and tools. However, modern btrfs filesystem mkswapfile and updated filefrag usually handle this correctly. If issues arise, the dedicated tool btrfs\_map\_physical may be required, though filefrag is generally sufficient on kernels \> 5.0.16

### **5.3 Bootloader Configuration**

These parameters must be passed to the kernel at boot.

#### **5.3.1 GRUB Configuration**

Edit /etc/default/grub and append to the GRUB\_CMDLINE\_LINUX\_DEFAULT string.

Bash

GRUB\_CMDLINE\_LINUX\_DEFAULT="quiet splash resume=UUID=a1b2-c3d4... resume\_offset=34816"

* **UUID:** The UUID of the *root partition* (or whichever partition holds the swapfile). Find this using findmnt \-no UUID \-T /swapfile.  
* **resume\_offset:** The number derived from filefrag.

After editing, regenerate the configuration:

* **Arch/Manjaro:** grub-mkconfig \-o /boot/grub/grub.cfg  
* **Debian/Ubuntu:** update-grub  
* **Fedora:** grub2-mkconfig \-o /boot/grub2/grub.cfg.9

#### **5.3.2 Systemd-boot**

For systems using systemd-boot, edit the loader entry in /boot/loader/entries/options.conf (or similar) to append the parameters to the options line.

## **6\. The Initramfs: Early Userspace Orchestration**

The kernel parameters instruct the kernel *what* to do, but the Initial RAM Filesystem (initramfs) provides the tools to *do* it. The initramfs must contain the modules and hooks necessary to read the resume device before the main root filesystem is mounted.  
Different distributions use different generators. Identifying the correct generator is critical.

### **6.1 Arch Linux & Manjaro (mkinitcpio)**

Arch uses mkinitcpio. The configuration resides in /etc/mkinitcpio.conf.  
The resume hook must be added to the HOOKS array. Placement is vital:

* It must be **after** udev (so the block device is detected).  
* It must be **before** filesystems (so the resume happens before filesystems are checked/mounted).

**Correct Configuration:**

Bash

HOOKS=(base udev autodetect modconf block filesystems resume fsck)

*Note: In some LVM/Encryption setups, resume might need to be after encrypt or lvm2.*  
Regenerate the image:

Bash

sudo mkinitcpio \-P

.6

### **6.2 Fedora & RHEL (dracut)**

Dracut is highly automated. It typically detects the resume kernel parameter and includes the necessary module. However, to force inclusion, creating a config file is recommended.  
Create /etc/dracut.conf.d/resume.conf:

Bash

add\_dracutmodules+=" resume "

Regenerate the initramfs:

Bash

sudo dracut \-f \--regenerate-all

.22

### **6.3 Debian & Ubuntu (initramfs-tools)**

Debian uses initramfs-tools. It usually auto-detects swap partitions, but swap files often require explicit declaration in a specialized config file.  
Create or edit /etc/initramfs-tools/conf.d/resume:

Bash

RESUME=UUID=a1b2-c3d4...  
RESUME\_OFFSET=34816

Update the initramfs:

Bash

sudo update-initramfs \-u

.18

## **7\. Systemd Sleep Orchestration: The Hybrid Workflow**

With the storage and kernel plumbing in place, the final layer is the user-facing behavior managed by systemd-logind and systemd-sleep. We aim to configure suspend-then-hibernate, which leverages our dual-swap architecture.

### **7.1 Configuring sleep.conf**

The file /etc/systemd/sleep.conf (or better, a drop-in like /etc/systemd/sleep.conf.d/hybrid.conf) controls the sleep logic.

Ini, TOML

\# /etc/systemd/sleep.conf.d/hybrid.conf

\# Enable the mode  
AllowSuspendThenHibernate=yes

\# Delay before transitioning from S3 (RAM) to S4 (Disk).  
\# 2 hours is a common balance for laptop usage.  
HibernateDelaySec=2h

\# Define the state for the 'suspend' phase (S3)  
SuspendState=mem

\# Define the mode for the 'hibernate' phase (S4)  
HibernateMode=platform

**Operational Logic:** When systemctl suspend-then-hibernate is invoked (or triggered by the lid switch), the system enters SuspendState=mem. ZRAM keeps the data alive. The system sets a hardware wake alarm for HibernateDelaySec (2 hours).

* **Scenario A:** The user opens the lid after 30 minutes. The system wakes instantly from RAM.  
* **Scenario B:** The user leaves the laptop overnight. The alarm fires after 2 hours. The system wakes up (dark wake), writes the RAM contents to the /swapfile (since ZRAM is volatile, it is dumped to disk along with everything else), and powers off completely.

### **7.2 Configuring logind.conf**

To map physical actions (lid close) to this mode, edit /etc/systemd/logind.conf.

Ini, TOML

\# /etc/systemd/logind.conf

\[Login\]  
\# Trigger hybrid mode on lid close  
HandleLidSwitch=suspend-then-hibernate  
HandleLidSwitchExternalPower=suspend-then-hibernate

\# Optional: Hibernate if idle for extended periods  
IdleAction=suspend-then-hibernate  
IdleActionSec=30min

Restart logind to apply: systemctl restart systemd-logind.7

## **8\. Advanced Optimization and Tuning**

To ensure the ZRAM device effectively masks the slowness of the disk swap (preventing the kernel from swapping to disk prematurely), specific Virtual Memory (VM) parameters must be tuned.

### **8.1 Swappiness and ZRAM**

The vm.swappiness parameter controls the kernel's preference for evicting anonymous pages (swap) versus file pages (dropping cache).

* **Traditional (Disk Swap):** Low swappiness (e.g., 60 or 10\) is used to avoid disk I/O.  
* **ZRAM Architecture:** High swappiness is desired. Since ZRAM is fast CPU-bound RAM, swapping out anonymous memory is cheap. We want to maximize the file cache to keep the system responsive.

**Recommended Settings (/etc/sysctl.d/99-zram.conf):**

Ini, TOML

\# Aggressively use swap (ZRAM) to preserve file cache.  
\# Values up to 200 are valid in modern kernels (meaning proactive swapping).  
vm.swappiness \= 180

\# Disable read-ahead.  
\# ZRAM is random-access; reading blocks ahead wastes CPU on decompression.  
vm.page-cluster \= 0

\# Adjust watermark scale to avoid direct reclaim stalls.  
vm.watermark\_scale\_factor \= 125

This configuration forces the kernel to utilize the priority-100 ZRAM device heavily, keeping the priority-0 disk swap empty until the hibernation trigger forces a dump of the entire memory state.1

### **8.2 Image Size Tuning**

The /sys/power/image\_size tunable acts as a ceiling for the hibernation image. By default, it is \~2/5 of RAM. If you have a small swap file (e.g., exactly RAM size) and heavy memory usage, you might want to ensure the image fits.  
Writing 0 to this file instructs the kernel to compress the image as much as possible and drop all non-essential cache before writing to disk.  
Systemd Tmpfiles Config (/etc/tmpfiles.d/hibernate-size.conf):  
w /sys/power/image\_size \- \- \- \- 0  
This maximizes the chance of successful hibernation even with smaller swap files, at the cost of slightly longer hibernation time.6

## **9\. Security: Encryption and Secure Boot**

### **9.1 Encrypted Swap (LUKS)**

If the root filesystem is encrypted (e.g., LUKS), the swap file inside it is naturally encrypted at rest. However, the kernel needs to be able to read it before unlocking the full system.

* **LVM on LUKS:** If the swap is a logical volume inside an encrypted container, the resume parameter usually points to /dev/mapper/vg-swap. The initramfs must contain the encrypt and lvm2 hooks *before* the resume hook to unlock the container first.  
* **Swapfile on LUKS:** Similar logic. The encrypt hook asks for the password, mounts the mapped device, and then the resume hook finds the offset on the mapped device.

### **9.2 Secure Boot and Lockdown**

When Secure Boot is enabled, the Linux kernel often enters "Lockdown" mode. Depending on the strictness (Integrity vs. Confidentiality), hibernation might be disabled. This is because replacing the running kernel image with one from disk (resume) is a theoretical vector for circumvention of Secure Boot.  
If cat /sys/kernel/security/lockdown indicates \[confidentiality\], hibernation is likely blocked. In such cases, one must either disable Secure Boot or use signed hibernation images (which is complex and distro-dependent).13

## **10\. Troubleshooting and Diagnostics**

The complexity of this stack means failures can occur at multiple layers.

### **10.1 Diagnostic Workflow**

1\. Verify Swap Hierarchy:  
Run zramctl and swapon \-s.

* *Success Criteria:* /dev/zram0 exists with Priority 100\. /swapfile exists with Priority 0\.  
* *Failure:* If ZRAM is missing, check systemctl status systemd-zram-setup@zram0. If /swapfile is missing, check /etc/fstab syntax.

2\. Verify Resume Offset:  
Check the kernel's view of the offset:

Bash

cat /sys/power/resume\_offset

Compare this with the filefrag output. They **must** match. If they differ, the bootloader parameters are not being applied (check cat /proc/cmdline).  
3\. Test Hibernation Manually:  
Run systemctl hibernate.

* *Error: "Not enough swap space":* The kernel isn't seeing the persistent swap or it's too small. Check /sys/power/image\_size.  
* *Error: "Write error":* Disk full or permission issues.  
* *System hangs on resume:* Often GPU driver related. If using Nvidia, enable the preservation services:  
  Bash  
  systemctl enable nvidia-suspend nvidia-hibernate nvidia-resume

4\. Check Logs:  
Detailed failure reasons are in the kernel ring buffer.

Bash

dmesg | grep \-i 'PM:'

Look for "Image not found" (bad resume param) or "Decompression failed".28

## **11\. Conclusion**

The "Split-Horizon" memory architecture represents the state-of-the-art in Linux power management for workstations and laptops. By acknowledging the distinct roles of ZRAM (performance augmentation) and Disk Swap (state persistence) and configuring them in a strict priority hierarchy, administrators can achieve a system that is responsive, memory-efficient, and capable of long-term state preservation.  
Success relies on the meticulous orchestration of the systemd-zram-generator for priority-100 compressed swap, the accurate calculation of physical offsets for priority-0 hibernation files, and the seamless handover managed by suspend-then-hibernate. While the setup requires precise configuration across bootloaders, initramfs, and systemd units, the result is a cohesive environment that maximizes the utility of modern hardware resources.

#### **Works cited**

1. Zram vs swap partition vs swapfile \- Newbie \- EndeavourOS Forum, accessed on December 16, 2025, [https://forum.endeavouros.com/t/zram-vs-swap-partition-vs-swapfile/69627](https://forum.endeavouros.com/t/zram-vs-swap-partition-vs-swapfile/69627)  
2. zram \- ArchWiki, accessed on December 16, 2025, [https://wiki.archlinux.org/title/Zram](https://wiki.archlinux.org/title/Zram)  
3. Installation, Configuration and Management of zram on SUSE Linux Micro, accessed on December 16, 2025, [https://documentation.suse.com/sle-micro/6.1/pdf/Micro-zram\_en.pdf](https://documentation.suse.com/sle-micro/6.1/pdf/Micro-zram_en.pdf)  
4. \[Solved\]Issue with using zram as swap. / Newbie Corner / Arch Linux Forums, accessed on December 16, 2025, [https://bbs.archlinux.org/viewtopic.php?id=301424](https://bbs.archlinux.org/viewtopic.php?id=301424)  
5. systemd-sleep.conf \- Freedesktop.org, accessed on December 16, 2025, [https://www.freedesktop.org/software/systemd/man/systemd-sleep.conf.html](https://www.freedesktop.org/software/systemd/man/systemd-sleep.conf.html)  
6. Power management/Suspend and hibernate \- ArchWiki, accessed on December 16, 2025, [https://wiki.archlinux.org/title/Power\_management/Suspend\_and\_hibernate](https://wiki.archlinux.org/title/Power_management/Suspend_and_hibernate)  
7. suspend and hibernate work but suspend-then-hibernate not / Newbie Corner / Arch Linux Forums, accessed on December 16, 2025, [https://bbs.archlinux.org/viewtopic.php?id=281373](https://bbs.archlinux.org/viewtopic.php?id=281373)  
8. Systemd unit generator for zram devices \- GitHub, accessed on December 16, 2025, [https://github.com/systemd/zram-generator](https://github.com/systemd/zram-generator)  
9. \[HowTo\] Add a backing SWAP device to zram (and enable hibernation), accessed on December 16, 2025, [https://forum.manjaro.org/t/howto-add-a-backing-swap-device-to-zram-and-enable-hibernation/168639](https://forum.manjaro.org/t/howto-add-a-backing-swap-device-to-zram-and-enable-hibernation/168639)  
10. Speed Up Your Linux System with Zram | Lorenzo Bettini, accessed on December 16, 2025, [https://www.lorenzobettini.it/2025/06/speed-up-your-linux-system-with-zram/](https://www.lorenzobettini.it/2025/06/speed-up-your-linux-system-with-zram/)  
11. Zram vs swap partition vs swapfile \- Page 2 \- Newbie \- EndeavourOS Forum, accessed on December 16, 2025, [https://forum.endeavouros.com/t/zram-vs-swap-partition-vs-swapfile/69627?page=2](https://forum.endeavouros.com/t/zram-vs-swap-partition-vs-swapfile/69627?page=2)  
12. Zswap vs zram in 2023, what's the actual practical difference? : r/linux \- Reddit, accessed on December 16, 2025, [https://www.reddit.com/r/linux/comments/11dkhz7/zswap\_vs\_zram\_in\_2023\_whats\_the\_actual\_practical/](https://www.reddit.com/r/linux/comments/11dkhz7/zswap_vs_zram_in_2023_whats_the_actual_practical/)  
13. How to setup Zram writeback device? : r/Gentoo \- Reddit, accessed on December 16, 2025, [https://www.reddit.com/r/Gentoo/comments/1ifvwsx/how\_to\_setup\_zram\_writeback\_device/](https://www.reddit.com/r/Gentoo/comments/1ifvwsx/how_to_setup_zram_writeback_device/)  
14. Hibernation not working "HibernateLocation via EFI variable is not possible.", accessed on December 16, 2025, [https://discussion.fedoraproject.org/t/hibernation-not-working-hibernatelocation-via-efi-variable-is-not-possible/120365](https://discussion.fedoraproject.org/t/hibernation-not-working-hibernatelocation-via-efi-variable-is-not-possible/120365)  
15. Setup hibernation on Silverblue / Kinoite? \- \#17 by aaravchen \- Fedora Discussion, accessed on December 16, 2025, [https://discussion.fedoraproject.org/t/setup-hibernation-on-silverblue-kinoite/78834/17](https://discussion.fedoraproject.org/t/setup-hibernation-on-silverblue-kinoite/78834/17)  
16. Can't seem to get hibernation to work properly \- EndeavourOS Forum, accessed on December 16, 2025, [https://forum.endeavouros.com/t/cant-seem-to-get-hibernation-to-work-properly/5933](https://forum.endeavouros.com/t/cant-seem-to-get-hibernation-to-work-properly/5933)  
17. using zram \- LinuxQuestions.org, accessed on December 16, 2025, [https://www.linuxquestions.org/questions/slackware-14/using-zram-4175737509-print/page2.html](https://www.linuxquestions.org/questions/slackware-14/using-zram-4175737509-print/page2.html)  
18. Hibernation/Hibernate\_Without\_Swap\_Partition \- Debian Wiki, accessed on December 16, 2025, [https://wiki.debian.org/Hibernation/Hibernate\_Without\_Swap\_Partition](https://wiki.debian.org/Hibernation/Hibernate_Without_Swap_Partition)  
19. Hibernate not working with swapfile \- Help \- NixOS Discourse, accessed on December 16, 2025, [https://discourse.nixos.org/t/hibernate-not-working-with-swapfile/69440](https://discourse.nixos.org/t/hibernate-not-working-with-swapfile/69440)  
20. How to add hibernation to Arch Linux using a swapfile \- GitHub Gist, accessed on December 16, 2025, [https://gist.github.com/Aikufurr/00daae657631e2c9d9506f38734696a0](https://gist.github.com/Aikufurr/00daae657631e2c9d9506f38734696a0)  
21. Ubuntu 22.04 Hibernate Using Swap File \- DEV Community, accessed on December 16, 2025, [https://dev.to/dansteren/ubuntu-2204-hibernate-using-swap-file-1ca1](https://dev.to/dansteren/ubuntu-2204-hibernate-using-swap-file-1ca1)  
22. How to use swap file for hibernation and hybrid sleep \- OpenMandriva forum, accessed on December 16, 2025, [https://forum.openmandriva.org/t/how-to-use-swap-file-for-hibernation-and-hybrid-sleep/4251](https://forum.openmandriva.org/t/how-to-use-swap-file-for-hibernation-and-hybrid-sleep/4251)  
23. regenerating initramfs / Kernel & Hardware / Arch Linux Forums, accessed on December 16, 2025, [https://bbs.archlinux.org/viewtopic.php?id=137019](https://bbs.archlinux.org/viewtopic.php?id=137019)  
24. dracut \- ArchWiki, accessed on December 16, 2025, [https://wiki.archlinux.org/title/Dracut](https://wiki.archlinux.org/title/Dracut)  
25. initramfs-tools \- an introduction to writing scripts for mkinitramfs \- Ubuntu Manpage, accessed on December 16, 2025, [https://manpages.ubuntu.com/manpages/bionic/man8/initramfs-tools.8.html](https://manpages.ubuntu.com/manpages/bionic/man8/initramfs-tools.8.html)  
26. Guide: Set up Suspend-then-hibernate \- Framework Laptops \- Universal Blue \- Discourse, accessed on December 16, 2025, [https://universal-blue.discourse.group/t/guide-set-up-suspend-then-hibernate/7193](https://universal-blue.discourse.group/t/guide-set-up-suspend-then-hibernate/7193)  
27. System Sleep States \- The Linux Kernel documentation, accessed on December 16, 2025, [https://docs.kernel.org/admin-guide/pm/sleep-states.html](https://docs.kernel.org/admin-guide/pm/sleep-states.html)  
28. Monitor not turning on after hibernating / Newbie Corner / Arch Linux Forums, accessed on December 16, 2025, [https://bbs.archlinux.org/viewtopic.php?id=310273](https://bbs.archlinux.org/viewtopic.php?id=310273)  
29. Problems Hibernating with swap file \- antiX-forum, accessed on December 16, 2025, [https://www.antixforum.com/forums/topic/problems-hibernating-with-swap-file/](https://www.antixforum.com/forums/topic/problems-hibernating-with-swap-file/)