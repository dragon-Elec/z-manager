# Identity
/home/ray/Desktop/files/wrk/prjkt-z/z-manager/core/hibernation
Handles full hibernation lifecycle: swap orchestration, resume parameter configuration (GRUB/initramfs), and readiness probing.

# Rules
None.

# Atomic Notes
!Pattern: [Read-Oriented Separation] - Reason: prober is read-only ("Safe Zone"); provisioner is destructive ("Hazard Zone").
!Pattern: [Btrfs COW Handling] - Reason: Swapfiles on Btrfs require `chattr +C` for kernel compatibility.
!Decision: [initramfs-tools priority] - Reason: Resume config currently prioritizes GRUB and initramfs-tools; dracut/mkinitcpio support is limited.

# Index
__init__.py: Registry of core hibernation orchestrators and models.
types.py: Shared data structures and results.
prober.py: Detection and offset/UUID discovery.
provisioner.py: Kernel node (swap) management and systemd units.
configurator.py: High-level orchestration, bootloader/initramfs config.

# Audits

### [FILE: types.py] [DONE]
Role: Shared data structures and models for hibernation.

/DNA/: [dataclasses(frozen=True) => model snapshots of state/results]

- SrcDeps: None
- SysDeps: dataclasses, typing

API:
  - HibernateCheckResult: Readiness state (ready, secure_boot, swap/ram).
  - SwapCreationResult: Created swap properties (path, uuid, offset).
  - ResumeConfig: Parameters for kernel resume capability.
  - SwapPersistResult: Outcome of systemd unit activation.
  - SwapTeardownResult: Results of swap removal/deactivation.
  - HibernateSetupResult: Full status of the orchestrated setup process.


### [FILE: prober.py] [DONE]
Role: Safe-zone system probing and property resolution.

/DNA/: [busctl/sysfs => readiness] + [filefrag/btrfs => offset] + [blkid => UUID]

- SrcDeps: .types, core.utils{common, block, swap}
- SysDeps: typing

API:
  - get_memory_info() -> tuple[int, int]: Returns total RAM and Swap in bytes.
  - check_hibernation_readiness() -> HibernateCheckResult: Validates logind and kernel support.
  - get_resume_offset(path) -> int | None: Calculates physical swapfile offset.
  - get_partition_uuid(path) -> str | None: Resolves UUID for block device or file host.


### [FILE: provisioner.py] [DONE]
Role: Hazard-zone swap lifecycle and unit management.

/DNA/: [if(btrfs) -> chattr +C] + [fallocate/dd -> mkswap] + [systemd-escape => unit] + [pkexec_write => /etc/systemd/system]

- SrcDeps: .types, .prober, core.utils{common, io, block, privilege}
- SysDeps: logging, os, shutil, pathlib

API:
  - create_swapfile(path, size_mb) -> SwapCreationResult: Safely initializes swap target.
  - enable_swapon(path, priority) -> bool: Activates swap via swapon.
  - swapoff_swap(path) -> bool: Deactivates swap via swapoff.
  - delete_swap(path) -> SwapTeardownResult: Stops swap and removes associated units/files.
  - escape_unit_name(path) -> str: Escapes path for systemd unit name.
  - generate_swap_unit(path, priority) -> str: Generates .swap unit content.
  - persist_swap_unit(path, priority) -> SwapPersistResult: Enables persistent systemd .swap unit.


### [FILE: configurator.py] [DONE]
Role: High-level orchestrator for boot and service configuration.

/DNA/: [pkexec_write(GRUB/initramfs) -> update-grub -> update-initramfs]

- SrcDeps: .types, .prober, .provisioner, core.utils{common, io, block, bootloader, kernel_cmdline, grub_paths}
- SysDeps: logging, os, shutil, subprocess, pathlib

API:
  - update_grub_resume(uuid, offset) -> tuple[bool, str]: Configures kernel params in GRUB.
  - configure_initramfs_resume(uuid, offset) -> tuple[bool, str]: Configures initramfs-tools resume.
  - pkexec_update_grub() -> tuple[bool, str]: Orchestrates GRUB config regeneration.
  - pkexec_update_initramfs() -> tuple[bool, str]: Orchestrates initramfs regeneration.
  - apply_full_setup(swap_path, size_mb, priority) -> HibernateSetupResult: Executes end-to-end configuration.
