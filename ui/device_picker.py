import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Pango
from core.utils.block import list_block_devices

class DevicePickerDialog(Adw.Window):
    """
    A modal dialog for selecting a block device or a folder for swapfiles.
    Includes filtering, visual safety checks, and "Power User" details (/dev/sdX).
    """
    __gtype_name__ = 'DevicePickerDialog'

    # Signal to return the selected path (e.g., "/dev/sda2" or "/home/user")
    __gsignals__ = {
        'device-selected': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, parent=None):
        super().__init__(modal=True, transient_for=parent)
        self.set_default_size(500, 650)
        self.set_title("Select Hibernate Storage")

        # Main Layout
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.content)

        # Header Bar
        header = Adw.HeaderBar()
        self.content.append(header)

        # Scrolled Window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.content.append(scrolled)

        # Container for both Folder selection and Device List
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_container.set_margin_top(12)
        self.main_container.set_margin_bottom(12)
        self.main_container.set_margin_start(12)
        self.main_container.set_margin_end(12)
        scrolled.set_child(self.main_container)

        # 1. Folder Selection Section
        folder_group = Adw.PreferencesGroup(
            title="Swapfile Location",
            description="Create a persistent swapfile on an existing filesystem."
        )
        self.main_container.append(folder_group)

        self.folder_row = Adw.ActionRow(title="Use a Swapfile", subtitle="Recommended for most users")
        self.folder_row.set_icon_name("folder-symbolic")
        folder_group.add(self.folder_row)

        folder_btn = Gtk.Button(label="Select Folder")
        folder_btn.set_valign(Gtk.Align.CENTER)
        folder_btn.add_css_class("suggested-action")
        folder_btn.connect("clicked", self._on_select_folder_clicked)
        self.folder_row.add_suffix(folder_btn)

        # 2. Block Device Section
        device_group = Adw.PreferencesGroup(
            title="Block Devices",
            description="Dedicated partitions for hibernation (Fastest)."
        )
        self.main_container.append(device_group)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        device_group.add(self.list_box)
        
        # Populate
        self._populate_list()

    def _populate_list(self):
        devices = list_block_devices()
        
        if not devices:
            self.list_box.append(Adw.ActionRow(title="No suitable devices found"))
            return

        # Track which disks have partitions to avoid the "Empty Disk" trap
        disks_with_parts = set()
        for dev in devices:
            path = dev.get('path', '')
            # If it's a partition (e.g. sda1), the parent disk (sda) is not safe
            if dev.get('type') == 'part':
                parent = path.rstrip('0123456789')
                disks_with_parts.add(parent)

        for dev in devices:
            self._add_device_row(dev, disks_with_parts)

    def _add_device_row(self, dev, disks_with_parts):
        path = dev.get('path')
        name = dev.get('name')
        label = dev.get('label')
        fstype = dev.get('fstype')
        size = dev.get('size')
        dev_type = dev.get('type')
        
        # 1. Determine Safety
        is_safe = True
        safety_msg = "Safe (Swap/Empty)"
        icon_name = "drive-harddisk-symbolic"

        if fstype and fstype != 'swap':
            is_safe = False
            safety_msg = f"Contains {fstype}"
        
        if dev.get('mountpoint'):
            is_safe = False
            safety_msg = f"Mounted at {dev.get('mountpoint')}"
        
        if path in disks_with_parts and dev_type == 'disk':
            is_safe = False
            safety_msg = "Contains partitions"

        # 2. UI Elements
        title = f"{label} ({size})" if label else f"{name} ({size})"
        extras = [path]
        if fstype: extras.append(fstype)
        if dev.get('model'): extras.append(dev.get('model'))
        subtitle = " • ".join([str(x) for x in extras if x])

        row = Adw.ActionRow(title=title, subtitle=subtitle)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        if not is_safe:
            icon.add_css_class("warning")
        row.add_prefix(icon)

        btn = Gtk.Button(label="Select" if is_safe else "Overwrite")
        btn.set_valign(Gtk.Align.CENTER)
        btn.add_css_class("suggested-action" if is_safe else "destructive-action")
        btn.connect("clicked", self._on_selected, path)
        row.add_suffix(btn)
        
        if not is_safe:
            lbl = Gtk.Label(label=safety_msg)
            lbl.add_css_class("dim-label")
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_margin_end(10)
            row.add_suffix(lbl)

        self.list_box.append(row)

    def _on_select_folder_clicked(self, btn):
        dialog = Gtk.FileDialog(title="Select Folder for Swapfile")
        dialog.select_folder(self, None, self._on_folder_dialog_response)

    def _on_folder_dialog_response(self, dialog, result):
        try:
            file = dialog.select_folder_finish(result)
            if file:
                path = file.get_path()
                self.emit("device-selected", path)
                self.close()
        except Exception:
            pass

    def _on_selected(self, btn, path):
        self.emit("device-selected", path)
        self.close()
