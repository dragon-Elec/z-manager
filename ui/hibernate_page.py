# zman/ui/hibernate_page.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

import os
import threading

from core.hibernation import (
    check_hibernation_readiness,
    detect_resume_swap,
    apply_full_setup,
)
from core.hibernation.provisioner import enable_swapon
from core.utils.block import is_block_device, check_device_safety
from ui.device_picker import DevicePickerDialog


class HibernatePage(Adw.PreferencesPage):
    """
    Page for managing System Hibernation settings.
    Built purely in Python to avoid XML template overhead for this minimal implementation.
    """

    __gtype_name__ = "HibernatePage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Hibernation")
        self.set_icon_name("system-suspend-hibernate-symbolic")

        self.readiness = None

        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        self.status_group = Adw.PreferencesGroup(title="System Status")
        self.add(self.status_group)

        self.status_row = Adw.ActionRow(title="Checking...")
        self.status_icon = Gtk.Image(icon_name="system-help-symbolic")
        self.status_row.add_prefix(self.status_icon)
        self.status_group.add(self.status_row)

        self.swap_group = Adw.PreferencesGroup(
            title="Persistent Storage",
            description="Hibernation requires a dedicated disk swap device.",
        )
        self.add(self.swap_group)

        self.create_swap_row = Adw.ActionRow(
            title="Resume Storage", subtitle="None detected"
        )
        self.swap_group.add(self.create_swap_row)

        self.create_swap_btn = Gtk.Button(label="Setup")
        self.create_swap_btn.set_valign(Gtk.Align.CENTER)
        self.create_swap_btn.connect("clicked", self._on_setup_swap_clicked)
        self.create_swap_row.add_suffix(self.create_swap_btn)

        self.boot_group = Adw.PreferencesGroup(
            title="Boot Configuration",
            description="Kernel parameters required for resuming.",
        )
        self.add(self.boot_group)

        self.boot_row = Adw.ActionRow(
            title="Kernel Resume Parameter", subtitle="Unknown"
        )
        self.boot_group.add(self.boot_row)

        self.apply_boot_btn = Gtk.Button(label="Apply Config")
        self.apply_boot_btn.set_valign(Gtk.Align.CENTER)
        self.apply_boot_btn.set_sensitive(False)
        self.apply_boot_btn.connect("clicked", self._on_apply_boot_clicked)
        self.boot_row.add_suffix(self.apply_boot_btn)

    def _refresh_state(self):
        self.readiness = check_hibernation_readiness()

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
            self.status_row.remove_css_class("success")

        active_swap = detect_resume_swap()
        if active_swap:
            self.create_swap_row.set_subtitle(f"Active: {active_swap}")
            self.create_swap_btn.set_label("Re-Configure")
            self.apply_boot_btn.set_sensitive(True)
        else:
            self.create_swap_row.set_subtitle("No suitable resume swap detected")
            self.create_swap_btn.set_label("Create")
            self.apply_boot_btn.set_sensitive(False)

        from core.hibernation import is_kernel_param_active

        if is_kernel_param_active("resume="):
            self.boot_row.set_subtitle("Resume parameter active")
            self.apply_boot_btn.set_label("Update Config")
        else:
            self.boot_row.set_subtitle("Missing 'resume=' parameter")
            self.apply_boot_btn.set_label("Apply Config")

    def _on_setup_swap_clicked(self, btn):
        root = self.get_root()
        dialog = DevicePickerDialog(parent=root)
        dialog.set_title("Select Partition for Hibernate Swap")
        dialog.connect("device-selected", self._on_device_selected)
        dialog.present()

    def _on_device_selected(self, dialog, path):
        target_path = path
        is_dev = is_block_device(path)

        if not is_dev:
            target_path = os.path.join(path, "swapfile")

        dialog.destroy()

        ram_gb = int(self.readiness.ram_total / 1024 / 1024 / 1024)
        confirm = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Setup Hibernate Swap",
            body=f"This will configure '{target_path}' as the hibernation resume device.\n\n"
            f"\u2022 If it's a file, it will be created ({ram_gb} GB+).\n"
            f"\u2022 If it's a partition, it will be formatted (DATA LOSS).\n\n"
            "Proceed?",
        )
        confirm.add_response("cancel", "Cancel")
        confirm.add_response("proceed", "Proceed")
        confirm.set_response_appearance("proceed", Adw.ResponseAppearance.SUGGESTED)

        confirm.connect(
            "response",
            lambda d, r: (
                self._start_setup_worker(target_path) if r == "proceed" else None
            ),
        )
        confirm.present()

    def _start_setup_worker(self, path):
        self.create_swap_btn.set_sensitive(False)
        self.create_swap_btn.set_label("Working...")

        thread = threading.Thread(target=self._setup_worker, args=(path,), daemon=True)
        thread.start()

    def _setup_worker(self, path):
        logs: list[str] = []
        success = False

        try:
            if not is_block_device(path):
                safe, msg = check_device_safety(os.path.dirname(path) or "/")
                if not safe:
                    raise Exception(f"Safety check failed: {msg}")
            else:
                safe, msg = check_device_safety(path)
                if not safe:
                    raise Exception(f"Safety check failed: {msg}")

            if not is_block_device(path):
                result = apply_full_setup(
                    path, size_mb=int(self.readiness.ram_total / 1024 / 1024) + 1024
                )
            else:
                result = apply_full_setup(path, size_mb=0)

            success = result.success
            logs.append(result.message)
            if result.reboot_required:
                logs.append("Please REBOOT to apply changes.")

        except Exception as e:
            logs.append(str(e))
            success = False

        GLib.idle_add(self._on_setup_finished, success, "\n".join(logs))

    def _on_setup_finished(self, success, log):
        self._refresh_state()

        heading = "Setup Complete" if success else "Setup Failed"
        dlg = Adw.MessageDialog(
            transient_for=self.get_root(), heading=heading, body=log
        )
        dlg.add_response("ok", "OK")
        dlg.present()

    def _on_apply_boot_clicked(self, btn):
        path = detect_resume_swap()
        if not path:
            return

        self.apply_boot_btn.set_sensitive(False)
        self.apply_boot_btn.set_label("Working...")

        thread = threading.Thread(target=self._boot_worker, args=(path,), daemon=True)
        thread.start()

    def _boot_worker(self, path):
        logs: list[str] = []
        success = False

        try:
            from core.hibernation import get_partition_uuid, get_resume_offset
            from core.hibernation.configurator import (
                update_grub_resume,
                configure_initramfs_resume,
                pkexec_update_grub,
                pkexec_update_initramfs,
            )

            uuid = get_partition_uuid(path)
            offset = get_resume_offset(path)

            if not uuid:
                raise Exception("Could not find UUID for device")

            ok, msg = update_grub_resume(uuid, offset)
            logs.append(f"GRUB: {msg}")
            if not ok:
                raise Exception("GRUB update failed")

            ok, msg = configure_initramfs_resume(uuid, offset)
            logs.append(f"initramfs: {msg}")

            logs.append("Regenerating initramfs (this may take a minute)...")
            ok_grub, _ = pkexec_update_grub()
            ok_init, msg_init = pkexec_update_initramfs()
            logs.append(msg_init)

            if ok_grub and ok_init:
                success = True
                logs.append("Please REBOOT to apply changes.")

        except Exception as e:
            logs.append(f"Error: {e}")

        GLib.idle_add(self._on_setup_finished, success, "\n".join(logs))
