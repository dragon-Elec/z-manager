# zman/ui/hibernate_page.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib

import threading
from core import hibernate_ctl, boot_config
from core.utils.common import read_file, run
from core.utils.block import is_block_device, check_device_safety
from ui.device_picker import DevicePickerDialog

class HibernatePage(Adw.PreferencesPage):
    """
    Page for managing System Hibernation settings.
    Built purely in Python to avoid XML template overhead for this minimal implementation.
    """
    __gtype_name__ = 'HibernatePage'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title("Hibernation")
        self.set_icon_name("system-suspend-hibernate-symbolic")
        
        # --- Internal State ---
        self.readiness = None
        
        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        # 1. Readiness Group (Status Header)
        self.status_group = Adw.PreferencesGroup(title="System Status")
        self.add(self.status_group)
        
        self.status_row = Adw.ActionRow(title="Checking...")
        self.status_icon = Gtk.Image(icon_name="system-help-symbolic")
        self.status_row.add_prefix(self.status_icon)
        self.status_group.add(self.status_row)

        # 2. Swap Storage Group
        self.swap_group = Adw.PreferencesGroup(title="Persistent Storage", description="Hibernation requires a dedicated disk swap device.")
        self.add(self.swap_group)
        
        # Action: Create Swap
        self.create_swap_row = Adw.ActionRow(title="Resume Storage", subtitle="None detected")
        self.swap_group.add(self.create_swap_row)
        
        self.create_swap_btn = Gtk.Button(label="Setup")
        self.create_swap_btn.set_valign(Gtk.Align.CENTER)
        self.create_swap_btn.connect("clicked", self._on_setup_swap_clicked)
        self.create_swap_row.add_suffix(self.create_swap_btn)

        # 3. Boot Config Group
        self.boot_group = Adw.PreferencesGroup(title="Boot Configuration", description="Kernel parameters required for resuming.")
        self.add(self.boot_group)
        
        self.boot_row = Adw.ActionRow(title="Kernel Resume Parameter", subtitle="Unknown")
        self.boot_group.add(self.boot_row)
        
        self.apply_boot_btn = Gtk.Button(label="Apply Config")
        self.apply_boot_btn.set_valign(Gtk.Align.CENTER)
        self.apply_boot_btn.set_sensitive(False) # Disabled until swap is ready
        self.apply_boot_btn.connect("clicked", self._on_apply_boot_clicked)
        self.boot_row.add_suffix(self.apply_boot_btn)

    def _refresh_state(self):
        """Refreshes the UI state."""
        # 1. Check Readiness
        self.readiness = hibernate_ctl.check_hibernation_readiness()
        
        if self.readiness.ready:
            self.status_row.set_title("System Ready")
            self.status_row.set_subtitle(self.readiness.message)
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.status_row.remove_css_class("error")
            self.status_row.add_css_class("success")
        else:
            self.status_row.set_title("Hibernation Unavailable")
            self.status_row.set_subtitle(self.readiness.message)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_row.add_css_class("error")

        # 2. Check Swap
        # We look for a device with priority start/end in /proc/swaps or known config
        # Simply checking active swaps for now
        # TODO: This is a bit simplistic. Ideally we check fstab + active.
        active_swap = self._find_resume_swap()
        if active_swap:
            self.create_swap_row.set_subtitle(f"Active: {active_swap}")
            self.create_swap_btn.set_label("Re-Configure")
            self.apply_boot_btn.set_sensitive(True)
        else:
            self.create_swap_row.set_subtitle("No suitable resume swap detected")
            self.create_swap_btn.set_label("Create")
            self.apply_boot_btn.set_sensitive(False)
            
        # 3. Check Boot Config
        if boot_config.is_kernel_param_active("resume="):
             self.boot_row.set_subtitle("Resume parameter active")
             # Mark button as "Update"
             self.apply_boot_btn.set_label("Update Config")
        else:
             self.boot_row.set_subtitle("Missing 'resume=' parameter")
             self.apply_boot_btn.set_label("Apply Config")

    def _find_resume_swap(self):
        """Heuristic to find the 'resume' swap (non-zram)."""
        try:
             # cat /proc/swaps
             # Filename Type Size Used Priority
             # /dev/zram0 partition ... 100
             # /swapfile file ... -2
             content = read_file("/proc/swaps")
             if content:
                 for line in content.splitlines()[1:]:
                     parts = line.split()
                     if len(parts) > 0:
                         path = parts[0]
                         if "zram" not in path:
                             return path
        except:
             pass
        return None

    def _on_setup_swap_clicked(self, btn):
        """Open dialog to pick partition or path."""
        # Reuse the existing DevicePickerDialog
        root = self.get_root()
        dialog = DevicePickerDialog(parent=root)
        dialog.set_title("Select Partition for Hibernate Swap")
        dialog.connect("device-selected", self._on_device_selected)
        dialog.present()

    def _on_device_selected(self, dialog, path):
        """User picked a partition. If they pick a mount point, we offer swapfile."""
        # Simple Logic:
        # If block device -> Use directly
        # If directory/mount -> Create /swapfile inside it
        
        target_path = path
        is_dev = is_block_device(path)
        
        if not is_dev:
            # Assume it's a mount point, append /swapfile
            target_path = os.path.join(path, "swapfile")
        
        dialog.destroy()
        
        # Confirm action
        confirm = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Setup Hibernate Swap",
            body=f"This will configure '{target_path}' as the hibernation resume device.\n\n"
                 f"• If it's a file, it will be created ({int(self.readiness.ram_total/1024/1024/1024)} GB+).\n"
                 f"• If it's a partition, it will be formatted (DATA LOSS).\n\n"
                 "Proceed?"
        )
        confirm.add_response("cancel", "Cancel")
        confirm.add_response("proceed", "Proceed") # ID 'proceed'
        confirm.set_response_appearance("proceed", Adw.ResponseAppearance.SUGGESTED)
        
        confirm.connect("response", lambda d, r: self._start_setup_worker(target_path) if r == "proceed" else None)
        confirm.present()

    def _start_setup_worker(self, path):
        # UI Lock
        self.create_swap_btn.set_sensitive(False)
        self.create_swap_btn.set_label("Working...")
        
        thread = threading.Thread(target=self._setup_worker, args=(path,), daemon=True)
        thread.start()

    def _setup_worker(self, path):
        logs = []
        success = False
        
        try:
            # 1. Size calculation (RAM + 1GB safety)
            ram_mb = int(self.readiness.ram_total / 1024 / 1024)
            size_mb = ram_mb + 1024
            
            # 2. Create (if file) or Format (if dev)
            # hibernate_ctl handles this distinction internally mostly, but let's check
            if not is_block_device(path):
                # Swapfile
                res = hibernate_ctl.create_swapfile(path, size_mb)
                if not res.success:
                    raise Exception(res.message)
                logs.append(f"Created swapfile at {path}")
            else:
                # Partition
                # Safety check
                safe, msg = check_device_safety(path)
                if not safe:
                     # Force fallback override? No, fail safe.
                     raise Exception(f"Device safety check failed: {msg}")
                
                run(["mkswap", path], check=True)
                logs.append(f"Formatted partition {path}")

            # 3. Enable Swapon
            if not hibernate_ctl.enable_swapon(path, priority=0):
                 logs.append("Warning: Could not enable swapon (maybe already active?)")
            else:
                 logs.append("Enabled swap device")
                 
            # 4. Fstab
            uuid = hibernate_ctl.get_partition_uuid(path)
            if uuid:
                if hibernate_ctl.update_fstab(path, uuid):
                    logs.append("Updated /etc/fstab with 'nofail'")
                else:
                    logs.append("Failed to update fstab")
            else:
                logs.append("Could not determine UUID for fstab")

            success = True
            
        except Exception as e:
            logs.append(str(e))
            success = False
            
        GLib.idle_add(self._on_setup_finished, success, "\n".join(logs))

    def _on_setup_finished(self, success, log):
        self._refresh_state()
        
        heading = "Setup Complete" if success else "Setup Failed"
        dlg = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=heading,
            body=log
        )
        dlg.add_response("ok", "OK")
        dlg.present()

    def _on_apply_boot_clicked(self, btn):
        # Need the active swap path
        path = self._find_resume_swap()
        if not path:
            return
            
        self.apply_boot_btn.set_sensitive(False)
        self.apply_boot_btn.set_label("Working...")
        
        thread = threading.Thread(target=self._boot_worker, args=(path,), daemon=True)
        thread.start()
    
    def _boot_worker(self, path):
        logs = []
        success = False
        
        try:
            uuid = hibernate_ctl.get_partition_uuid(path)
            offset = hibernate_ctl.get_resume_offset(path)
            
            if not uuid:
                raise Exception("Could not find UUID for device")
                
            # 1. Update GRUB
            res = boot_config.update_grub_resume(uuid, offset)
            logs.append(res.message)
            if not res.success:
                 raise Exception("GRUB update failed")
                 
            # 2. Update initramfs config
            res2 = boot_config.configure_initramfs_resume(uuid, offset)
            logs.append(res2.message)
            
            # 3. Regenerate
            # This is slow!
            logs.append("Regenerating initramfs (this may take a minute)...")
            res3 = boot_config.regenerate_initramfs()
            logs.append(res3.message)
            
            if res3.success:
                success = True
                logs.append("Please REBOOT to apply changes.")

        except Exception as e:
            logs.append(f"Error: {e}")
            
        GLib.idle_add(self._on_setup_finished, success, "\n".join(logs))
