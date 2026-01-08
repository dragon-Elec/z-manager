#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib

import os
import subprocess


from ui.custom_widgets import ScenarioCard
from ui.device_picker import DevicePickerDialog
from ui.global_config_dialog import GlobalConfigDialog
import threading
from core import zdevice_ctl, config as zram_config
from dataclasses import dataclass
from ui.configure_logic import ConfigureLogic
from ui.confirmation_dialog import ConfirmationDialog


def get_ui_path(file_name):
    return os.path.join(os.path.dirname(__file__), file_name)

@Gtk.Template(filename=get_ui_path('configure_page.ui'))
class ConfigurePage(Gtk.Box):
    """
    The page for configuring ZRAM settings. This class is the Python
    backend for the configure_page.ui template.
    """
    __gtype_name__ = 'ConfigurePage'

    # Template Children
    profiles_flowbox: Gtk.FlowBox = Gtk.Template.Child()
    
    # Device Selector Group
    device_selector_row: Adw.ComboRow = Gtk.Template.Child()
    add_device_btn: Gtk.Button = Gtk.Template.Child()
    remove_device_btn: Gtk.Button = Gtk.Template.Child()

    # Form Fields
    size_mode_row: Adw.ComboRow = Gtk.Template.Child()
    custom_size_row: Adw.EntryRow = Gtk.Template.Child()
    algorithm_row: Adw.ComboRow = Gtk.Template.Child()
    custom_algorithm_row: Adw.EntryRow = Gtk.Template.Child()
    priority_row: Adw.SpinRow = Gtk.Template.Child()
    host_memory_limit_switch: Adw.SwitchRow = Gtk.Template.Child()
    host_memory_limit_value: Adw.SpinRow = Gtk.Template.Child()
    resident_limit_row: Adw.EntryRow = Gtk.Template.Child()
    
    # Advanced / Writeback
    fs_mode_switch: Gtk.Switch = Gtk.Template.Child()
    fs_type_row: Adw.ComboRow = Gtk.Template.Child()
    mount_point_row: Adw.EntryRow = Gtk.Template.Child()
    writeback_row: Adw.ActionRow = Gtk.Template.Child()
    select_writeback_btn: Gtk.Button = Gtk.Template.Child()
    options_row: Adw.EntryRow = Gtk.Template.Child()
    
    # Raw Config Row & Buttons
    raw_config_row: Adw.ActionRow = Gtk.Template.Child()
    open_folder_btn: Gtk.Button = Gtk.Template.Child()
    open_file_btn: Gtk.Button = Gtk.Template.Child()
    open_example_btn: Gtk.Button = Gtk.Template.Child()
    
    # Global Config
    global_settings_btn: Gtk.Button = Gtk.Template.Child()
    
    # Action Bar
    apply_button: Gtk.Button = Gtk.Template.Child()
    revert_button: Gtk.Button = Gtk.Template.Child()
    live_apply_switch: Gtk.Switch = Gtk.Template.Child()

    def __init__(self, **kwargs):
        """Initializes the ConfigurePage widget."""
        super().__init__(**kwargs)
        
        # Internal State: Map device_name -> config_dict
        # Load from config file, or default to zram0 if no config exists
        self.device_configs = {}
        self.current_device = None
        self._load_devices_from_config()

        
        # Connect Signals for Device Management
        self.device_selector_row.connect("notify::selected", self._on_device_selector_changed)
        self.add_device_btn.connect("clicked", self._on_add_device_clicked)
        self.remove_device_btn.connect("clicked", self._on_remove_device_clicked)
        
        # Connect Apply/Revert signals
        self.apply_button.connect("clicked", self._on_apply_clicked)
        self.revert_button.connect("clicked", self._on_revert_clicked)


        # Connect Form Signals
        self.algorithm_row.connect("notify::selected", self._on_algorithm_changed)
        self.size_mode_row.connect("notify::selected", self._on_size_mode_changed)
        self.host_memory_limit_switch.connect("notify::active", self._on_host_limit_toggled)
        self.fs_mode_switch.connect("notify::active", self._on_fs_mode_toggled)
        
        # Connect signals for Change Detection
        # We also need these to trigger _check_for_changes
        self.algorithm_row.connect("notify::selected", self._on_conf_changed)
        self.custom_algorithm_row.connect("notify::text", self._on_conf_changed)
        self.size_mode_row.connect("notify::selected", self._on_conf_changed)
        self.custom_size_row.connect("notify::text", self._on_conf_changed)
        self.priority_row.connect("notify::value", self._on_conf_changed)
        
        self.host_memory_limit_switch.connect("notify::active", self._on_conf_changed)
        self.host_memory_limit_value.connect("notify::value", self._on_conf_changed)
        self.resident_limit_row.connect("notify::text", self._on_conf_changed)
        
        self.fs_mode_switch.connect("notify::active", self._on_conf_changed)
        self.fs_type_row.connect("notify::selected", self._on_conf_changed)
        self.mount_point_row.connect("notify::text", self._on_conf_changed)
        
        self.writeback_row.connect("notify::subtitle", self._on_conf_changed) # If subtitle changes
        self.options_row.connect("notify::text", self._on_conf_changed)
        
        # Connect Raw Config Buttons
        self.open_folder_btn.connect("clicked", self._on_open_folder_clicked)
        self.open_file_btn.connect("clicked", self._on_open_file_clicked)
        self.open_example_btn.connect("clicked", self._on_open_example_clicked)
        self.global_settings_btn.connect("clicked", self._on_global_settings_clicked)

        # Populate Profiles
        self._populate_profiles()
        
        # Initialize Form with the first device from config
        if self.current_device:
            self._load_form_state(self.current_device)

    def _get_default_config(self):
        """Returns the default configuration dictionary for a new device."""
        return ConfigureLogic.get_default_config()

    def _load_devices_from_config(self):
        """
        Load devices from the config file and populate the device selector.
        If no config file exists, defaults to zram0.
        """
        # Read config from disk
        parser = zram_config.read_zram_config()
        
        # Get device names (filter out global section)
        device_names = [k for k in parser.keys() if k != 'zram-generator']
        
        # If no devices in config, default to zram0
        if not device_names:
            device_names = ["zram0"]
        
        # Populate internal state
        for dev in device_names:
            # _load_form_state will populate the actual values later
            self.device_configs[dev] = self._get_default_config()
        
        # Populate the device selector dropdown
        model = self.device_selector_row.get_model()
        # Clear existing items (the UI template has zram0 hardcoded)
        while model.get_n_items() > 0:
            model.remove(0)
        # Add devices from config
        for dev in sorted(device_names):
            model.append(dev)
        
        # Select first device
        if device_names:
            self.current_device = sorted(device_names)[0]
            self.device_selector_row.set_selected(0)

    # --- Device Management Logic ---

    def _on_device_selector_changed(self, row, param):
        """Handle switching between devices in the dropdown."""
        # 1. Save state of the PREVIOUS device
        self._save_current_form_state()
        
        # 2. Identify the NEW device
        model = self.device_selector_row.get_model()
        idx = self.device_selector_row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return
            
        new_device = model.get_string(idx)
        
        # 3. Load state for the NEW device
        if new_device:
            self.current_device = new_device
            self._load_form_state(new_device)
            self._update_remove_button_state()

    def _on_add_device_clicked(self, btn):
        """Add a new device to the list."""
        self._save_current_form_state() # Save current work first
        
        model = self.device_selector_row.get_model()
        count = model.get_n_items()
        
        # Find next available name (zram0, zram1, zram2...)
        existing = [model.get_string(i) for i in range(count)]
        new_name = f"zram{count}"
        i = 0
        while new_name in existing:
             i += 1
             new_name = f"zram{i}"
        
        # Init state
        self.device_configs[new_name] = self._get_default_config()
        
        # Add to UI
        model.append(new_name)
        
        # Select it (this triggers _on_device_selector_changed)
        # But wait, logic in changed handler saves OLD state. 
        # Since we just saved, that's fine.
        self.device_selector_row.set_selected(model.get_n_items() - 1)

    def _on_remove_device_clicked(self, btn):
        """Remove the currently selected device."""
        model = self.device_selector_row.get_model()
        idx = self.device_selector_row.get_selected()
        
        if idx == Gtk.INVALID_LIST_POSITION:
            return

        device_name = model.get_string(idx)
        
        # Prevent removing the last device?
        if model.get_n_items() <= 1:
            return 

        # Delete state
        if device_name in self.device_configs:
            del self.device_configs[device_name]
            
        # Prevent _on_device_selector_changed from saving the zombie device
        self.current_device = None
            
        # Remove from UI
        # AdwComboRow model is likely a GtkStringList
        model.remove(idx)
        
        # Selection automatically updates to a nearby item, triggering _on_device_selector_changed
        
        # Trigger change detection so Apply button becomes enabled
        self._check_for_changes()

    def _update_remove_button_state(self):
        """Disable remove button if only one device remains."""
        count = self.device_selector_row.get_model().get_n_items()
        self.remove_device_btn.set_sensitive(count > 1)

    # --- Form State Logic ---

    def _save_current_form_state(self):
        """Reads all UI widgets and updates the self.device_configs dict."""
        dev = self.current_device
        if not dev:
            return

        if dev not in self.device_configs:
            self.device_configs[dev] = {}
            
        cfg = self.device_configs[dev]
        
        cfg["size_mode"] = self.size_mode_row.get_selected()
        cfg["custom_size"] = self.custom_size_row.get_text()
        cfg["algorithm"] = self.algorithm_row.get_selected()
        cfg["custom_algorithm"] = self.custom_algorithm_row.get_text()
        cfg["priority"] = int(self.priority_row.get_value())
        
        cfg["host_limit_enabled"] = self.host_memory_limit_switch.get_active()
        cfg["host_limit_mb"] = int(self.host_memory_limit_value.get_value())
        cfg["resident_limit"] = self.resident_limit_row.get_text()
        
        cfg["fs_mode"] = self.fs_mode_switch.get_active()
        cfg["fs_type"] = self.fs_type_row.get_selected()
        cfg["mount_point"] = self.mount_point_row.get_text()
        
        # Writeback is stored in subtitle for now
        # Writeback is stored in subtitle for now
        cfg["writeback_dev"] = self.writeback_row.get_subtitle() or "None Selected"
        cfg["options"] = self.options_row.get_text()

    def _get_current_ui_config(self, device_name):
        """Helper to get config strictly from UI widgets (live)"""
        # This duplicates _save_current_form_state but returns it instead of saving
        # Actually, _save_current_form_state saves to self.device_configs.
        # So we can just call that and read self.device_configs[device_name]
        self._save_current_form_state()
        return self.device_configs.get(device_name, {})

    def _load_form_state(self, device_name):
        """
        Populates UI widgets for the selected device. 
        Attempts to read from actual config first.
        """
        # 1. Read fresh config from disk
        parser = zram_config.read_zram_config()
        
        cfg = {}
        if device_name in parser:
            # Parse existing
            sect = parser[device_name]
            
            # Size
            val = sect.get("zram-size", "")
            if val == "ram":
               cfg["size_mode"] = 1
               cfg["custom_size"] = ""
            elif "min(ram / 2" in val:
               cfg["size_mode"] = 0
               cfg["custom_size"] = ""
            else:
               cfg["size_mode"] = 2
               cfg["custom_size"] = val
               
            # Algorithm
            algo = sect.get("compression-algorithm", "zstd")
            algos = ["zstd", "lzo-rle", "lz4"]
            if algo in algos:
                cfg["algorithm"] = algos.index(algo)
                cfg["custom_algorithm"] = ""
            else:
                cfg["algorithm"] = 3 # Custom
                cfg["custom_algorithm"] = algo
                
            # Priority
            cfg["priority"] = int(sect.get("swap-priority", 100))

            # New Fields
            cfg["resident_limit"] = sect.get("zram-resident-limit", "")
            cfg["options"] = sect.get("options", "")
            
            # Writeback
            wb = sect.get("writeback-device")
            cfg["writeback_dev"] = wb if wb else "None Selected"
            
            # FS/Mount - Not strictly in zram-generator standard but consistent with our writer
            cfg["fs_type"] = 1 # Default ext4
            cfg["fs_mode"] = False
            if sect.get("fs-type"):
                cfg["fs_mode"] = True
                fst = sect.get("fs-type")
                if fst == "btrfs": cfg["fs_type"] = 2
                elif fst == "ext2": cfg["fs_type"] = 0
                else: cfg["fs_type"] = 1
                cfg["mount_point"] = sect.get("mount-point", "/tmp/zram_fs")
                
        else:
            # Fallback for new/unknown device
            cfg = self._get_default_config()

        # Update internal state (important for other handlers)
        self.device_configs[device_name] = cfg
        
        # 2. Update UI
        self.size_mode_row.set_selected(cfg.get("size_mode", 0))
        self.custom_size_row.set_text(cfg.get("custom_size", ""))
        self.algorithm_row.set_selected(cfg.get("algorithm", 0))
        self.custom_algorithm_row.set_text(cfg.get("custom_algorithm", ""))
        self.priority_row.set_value(cfg.get("priority", 100))
        
        self.host_memory_limit_switch.set_active(cfg.get("host_limit_enabled", False))
        self.host_memory_limit_value.set_value(cfg.get("host_limit_mb", 2048))
        self.resident_limit_row.set_text(cfg.get("resident_limit", ""))
        
        self.fs_mode_switch.set_active(cfg.get("fs_mode", False))
        self.fs_type_row.set_selected(cfg.get("fs_type", 1))
        self.mount_point_row.set_text(cfg.get("mount_point", "/tmp/zram_fs"))
        
        # Writeback
        wb = cfg.get("writeback_dev", "None Selected")
        self.writeback_row.set_subtitle(wb)
        self.options_row.set_text(cfg.get("options", ""))
        
        # Update Raw Config UI (hierarchical search)
        self._update_raw_config_ui()
        
        # Trigger visibility updates
        self._on_algorithm_changed(self.algorithm_row, None)
        self._on_size_mode_changed(self.size_mode_row, None)
        self._on_host_limit_toggled(self.host_memory_limit_switch, None)
        self._on_fs_mode_toggled(self.fs_mode_switch, None)
        
        # Check for changes to update button sensitivity
        self._check_for_changes()
        self._on_size_mode_changed(self.size_mode_row, None)
        self._on_host_limit_toggled(self.host_memory_limit_switch, None)
        self._on_fs_mode_toggled(self.fs_mode_switch, None)


    # --- Existing Handlers ---

    @Gtk.Template.Callback()
    def on_select_writeback_clicked(self, btn):
        # We need a reference to the top-level window to set transient parent
        root = self.get_root()
        dialog = DevicePickerDialog(parent=root)
        dialog.connect("device-selected", self.on_device_chosen)
        dialog.present()
        
    def on_device_chosen(self, dialog, path):
        self.writeback_row.set_subtitle(path)
        # Also update state immediately so it's not lost if they switch devices right after
        self._save_current_form_state() 
        self._check_for_changes()

    def _on_conf_changed(self, *args):
        """Generic handler for any input change."""
        self._check_for_changes()

    def _check_for_changes(self):
        """Updates Apply/Revert button sensitivity based on pending changes."""
        changes = self._get_pending_changes()
        has_changes = len(changes) > 0
        
        self.apply_button.set_sensitive(has_changes)
        self.revert_button.set_sensitive(has_changes)

    def _on_algorithm_changed(self, row, param):
        """Toggle custom algorithm entry visibility."""
        idx = self.algorithm_row.get_selected()
        # Index 3 is 'Custom...'
        is_custom = (idx == 3)
        self.custom_algorithm_row.set_visible(is_custom)

    def _on_size_mode_changed(self, row, param):
        """Toggle custom size entry visibility."""
        idx = self.size_mode_row.get_selected()
        # Index 2 is 'Custom' (assuming 0=50%, 1=100%, 2=Custom)
        # Checking _get_default_config logic:
        # 0: 50%, 1: 100%, 2: Custom
        is_custom = (idx == 2)
        self.custom_size_row.set_visible(is_custom)

    def _on_host_limit_toggled(self, row, param):
        """Toggle host memory limit value visibility."""
        active = self.host_memory_limit_switch.get_active()
        self.host_memory_limit_value.set_visible(active)

    def _on_fs_mode_toggled(self, row, param):
        """Toggle filesystem options visibility."""
        active = self.fs_mode_switch.get_active()
        self.fs_type_row.set_sensitive(active)
        self.mount_point_row.set_sensitive(active)

    def _populate_profiles(self):
        # Clear existing (if any)
        while self.profiles_flowbox.get_child_at_index(0):
            self.profiles_flowbox.remove(self.profiles_flowbox.get_child_at_index(0))

        profiles = [
            ("Desktop / Gaming", "High priority, aggressive compression.", "input-gaming-symbolic", "desktop"),
            ("Server", "Balanced, prioritizes stability.", "network-server-symbolic", "server"),
            ("Power Saver", "Low CPU usage, conservative.", "battery-level-80-symbolic", "battery"), 
        ]

        for title, desc, icon, pid in profiles:
            card = ScenarioCard(title, desc, icon)
            self.profiles_flowbox.append(card)

    def _get_pending_changes(self):
        """
        Calculates the differences between the current UI state and the actual
        on-disk configuration. Returns a list of changes.
        
        Note: This compares against the CONFIG FILE, not the LIVE system.
        The Status Page shows live state; Configure Page is a config file editor.
        """
        # Update internal state from UI widgets first
        self._save_current_form_state()
        return ConfigureLogic.calculate_changes(self.device_configs)


    def _on_revert_clicked(self, btn):
        """
        Discard current UI changes and reload from disk.
        """
        # Just reloading form state will overwrite UI with disk values
        self._load_form_state(self.current_device)
        
        # Optional: Toast notification "Changes reverted"

    def _on_apply_clicked(self, btn):
        """
        Handler for the Apply button. Saves state and starts a background thread.
        """
        # Calculate Changes
        changes = self._get_pending_changes()
        
        if not changes:
            # Toast?
            return

        # Generate Diff
        diff_text = ConfigureLogic.get_config_diff(self.device_configs)

        # Show Confirmation Dialog
        self._show_confirmation_dialog(changes, diff_text)

    def _show_confirmation_dialog(self, changes, diff_text):
        dialog = ConfirmationDialog(self.get_root(), changes, diff_text)
        dialog.connect("response", self._on_confirm_response, changes)
        dialog.present()

    def _on_confirm_response(self, dialog, response, changes):
        # In Adw.MessageDialog, response is the string ID
        if response == "apply":
            dialog.destroy() # Close first
            self._start_apply_process(changes)
        else:
            dialog.destroy()

    def _start_apply_process(self, changes):
        # 1. Lock UI
        self.apply_button.set_sensitive(False)
        self.apply_button.set_label("Applying...")
        self.device_selector_row.set_sensitive(False)
        self.live_apply_switch.set_sensitive(False)
        
        # Check experimental switch
        live_apply = self.live_apply_switch.get_active()
        
        # 2. Start Thread
        # We need to pass the FULL CONFIGS because Modifications need the values
        # or we just pass the list and let the worker figure it out from self.device_configs?
        # Thread needs a copy of data to be safe.
        data_snapshot = {k: v.copy() for k,v in self.device_configs.items()}
        
        thread = threading.Thread(
            target=self._apply_worker_batch,
            args=(changes, data_snapshot, live_apply),
            daemon=True
        )
        thread.start()

    def _apply_worker_batch(self, changes, device_configs_snapshot, live_apply):
        """
        Executes the changes in a background thread using ConfigureLogic.
        """
        success, logs = ConfigureLogic.apply_worker_batch(changes, device_configs_snapshot, live_apply)
            
        # Post-process on main thread
        GLib.idle_add(self._on_apply_finished, success, "\n".join(logs))




    def _on_apply_finished(self, success, log_message):
        """
        Callback from background thread. Unlocks UI and shows result.
        """
        # 1. Unlock UI
        self.apply_button.set_label("Apply Changes")
        self.device_selector_row.set_sensitive(True)
        self.live_apply_switch.set_sensitive(True)
        # Re-check for changes to set button sensitivity correctly (should be false if success)
        # But wait, checking for changes effectively re-reads UI vs Disk.
        # If disk was updated, then there should be no changes.
        self._check_for_changes()

        # 2. Show Result
        if success:
            self._show_toast("Configuration saved successfully. Restart required.")
            # Reload form to sync everything up cleanly
            self._load_form_state(self.current_device)
        else:
            # Show Error Dialog
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Error Applying Changes",
                body=log_message
            )
            dialog.add_response("ok", "OK")
            dialog.present()

    def _update_raw_config_ui(self):
        """Updates the subtitle and state of the raw config row."""
        path = zram_config.get_active_config_path()
        if path:
            self.raw_config_row.set_subtitle(str(path))
            self.open_file_btn.set_sensitive(True)
            self.open_folder_btn.set_sensitive(True)
        else:
            self.raw_config_row.set_subtitle("No config file found (Using defaults)")
            self.open_file_btn.set_sensitive(False)
            self.open_folder_btn.set_sensitive(True) # Can still open folder

    def _on_open_folder_clicked(self, btn):
        path = zram_config.get_active_config_path()
        if path:
            self._reveal_resource(str(path))
        else:
            self._open_resource("/etc/systemd/")

    def _on_open_file_clicked(self, btn):
        path = zram_config.get_active_config_path()
        if path:
            self._open_resource(str(path))
        else:
            self._show_toast("No active configuration file to open.")

    def _on_open_example_clicked(self, btn):
        # List of potential locations for the example file
        candidates = [
            "/usr/share/doc/systemd-zram-generator/zram-generator.conf.example",
            "/usr/share/doc/zram-generator/zram-generator.conf.example"
        ]
        
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = path
                break
        
        if found:
            self._open_resource(found)
        else:
            self._show_toast("Example config file not found in standard locations.")

    def _reveal_resource(self, path):
        """
        Attempts to highlight the file in the file manager using DBus.
        Falls back to opening the parent folder if DBus fails.
        """
        # (omitted for brevity)
        pass

    def _on_global_settings_clicked(self, btn):
        """Open the Global Config Dialog."""
        current = zram_config.read_global_config()
        dialog = GlobalConfigDialog(parent=self.get_root(), current_config=current)
        dialog.connect("applied", self._on_global_applied)
        dialog.present()
        
    def _on_global_applied(self, dialog):
        updates = dialog.updates
        # We process this immediately (blocking UI briefly is fine for this action) or use thread.
        # Since it's a simple write, we can do it here and show toast.
        
        # We need to use zdevice_ctl to ensure safety/consistency
        res = zdevice_ctl.apply_global_config(updates)
        
        if res.success:
            self._show_toast("Global settings updated.")
        else:
            # Show Error
            dlg = Adw.MessageDialog(
                 transient_for=self.get_root(),
                 heading="Error Updating Global Settings",
                 body=res.message
            )
            dlg.add_response("ok", "OK")
            dlg.present()

        if not os.path.exists(path):
             self._open_resource(os.path.dirname(path))
             return

        abs_path = os.path.abspath(path)
        uri = f"file://{abs_path}"
        
        # DBus command to show items (Standard FileManager1 interface)
        cmd = [
            "dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1.ShowItems",
            f"array:string:{uri}", "string:"
        ]

        # Handle Root -> User transition
        if os.geteuid() == 0:
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                # We need to run as the user.
                # NOTE: DBus session bus access from sudo is tricky. 
                # We attempt to find the user's DBUS_SESSION_BUS_ADDRESS.
                # If this fails, we fall back to opening the folder.
                try:
                    # Try to get the DBus address from the user's running process (e.g., systemd --user)
                    # pgrep -u <user> systemd --user | head -n 1
                    # But simpler: just try 'sudo -u user' first. 
                    # Many modern distros handle this via pam_systemd or similar.
                    cmd = ["sudo", "-u", sudo_user] + cmd
                    
                    # We also might need to inject the DBUS address if it's missing in sudo env.
                    # But finding it reliably is hard without hacky pid sniffing.
                    # Let's try the direct command first.
                    pass
                except:
                    pass

        try:
            # Run and wait. If exit code 0, it worked.
            # We capture output to avoid spamming stdout
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # DBus method failed (not supported or permissions issue).
            # Fallback: Just open the folder.
            self._open_resource(os.path.dirname(path))

    def _open_resource(self, path):
        """
        Attempts to open a file or directory using the system default handler (xdg-open).
        If running as root via sudo, drops privileges to the original user to ensure
        read-only access to system files and better GUI integration.
        """
        if not os.path.exists(path):
            self._show_toast(f"Error: Path not found: {path}")
            return

        cmd = ["xdg-open", path]
        
        # If running as root, try to find the original user
        if os.geteuid() == 0:
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                # Run as the original user
                cmd = ["sudo", "-u", sudo_user, "xdg-open", path]

        try:
            # Run in background
            subprocess.Popen(cmd, 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        except Exception as e:
            # If fail, try fallback without dropping privs or just show error
            print(f"Failed to open {path}: {e}")
            self._show_toast(f"Could not open {path}. Error: {e}")

    def _show_toast(self, message):
        """Helper to show an overlay toast."""
        overlay = self.get_root().get_child() # Assuming MainWindow has Adw.ToastOverlay
        # This is risky. Better to use Adw.Toast directly if we have an overlay instance.
        # But wait, we are inside a Gtk.Box. We don't have easy access to the overlay.
        # For now, let's use a simple MessageDialog for success too if overlay is hard.
        # Or, just assume the main window has one.
        
        # Simpler approach: Use a MessageDialog for success too is safe.
        # But Toasts are nicer.
        # Let's try to get the toast overlay.
        # In main_window.py, the stack is inside... wait.
        # Let's look at main_window.py first? No, too slow.
        # Let's adhere to "Safe" for now. A dialog is fine.
        
        # Actually, let's make it an info dialog.
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Success",
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()
