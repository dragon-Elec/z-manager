import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Pango
from core import os_utils

class DevicePickerDialog(Adw.Window):
    """
    A modal dialog for selecting a block device.
    Includes filtering, visual safety checks, and "Power User" details (/dev/sdX).
    """
    __gtype_name__ = 'DevicePickerDialog'

    # Signal to return the selected path (e.g., "/dev/sda2")
    __gsignals__ = {
        'device-selected': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, parent=None):
        super().__init__(modal=True, transient_for=parent)
        self.set_default_size(500, 600)
        self.set_title("Select Writeback Device")

        # Main Layout
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content)

        # Header Bar
        header = Adw.HeaderBar()
        content.append(header)

        # Search Bar (Optional, but nice for power users)
        # search_entry = Gtk.SearchEntry()
        # header.set_title_widget(search_entry) # Or put in a toolbar view

        # List Area
        list_container = Gtk.ScrolledWindow()
        list_container.set_vexpand(True)
        content.append(list_container)

        # We use a GtkListBox with AdwActionRows for the items
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("rich-list") # Adwaita class
        list_container.set_child(self.list_box)
        
        # Populate
        self._populate_list()

    def _populate_list(self):
        devices = os_utils.list_block_devices()
        
        if not devices:
            # Empty state
            status = Adw.StatusPage()
            status.set_icon_name("drive-harddisk-symbolic")
            status.set_title("No Devices Found")
            status.set_description("Could not list block devices.")
            self.set_content(status)
            return

        for dev in devices:
            self._add_device_row(dev)

    def _add_device_row(self, dev):
        # dev is a dict: {name, path, size, type, label, fstype, mountpoint, model}
        
        path = dev.get('path')
        name = dev.get('name')
        label = dev.get('label')
        fstype = dev.get('fstype')
        size = dev.get('size')
        dev_type = dev.get('type')
        
        # 1. Determine Safety
        is_safe = True
        safety_msg = "Safe to use (Swap/Empty)"
        icon_name = "drive-harddisk-symbolic"
        color_class = "success"

        if fstype and fstype != 'swap':
            is_safe = False
            safety_msg = f"Contains {fstype} filesystem"
            color_class = "error"
        
        if dev.get('mountpoint'):
            is_safe = False
            safety_msg = f"Mounted at {dev.get('mountpoint')}"
            color_class = "error"

        # 2. Main Title: "Label (Size)" or "Name (Size)"
        if label:
            title = f"{label} ({size})"
        else:
            title = f"{name} ({size})"
            
        # 3. Subtitle: The "Power User" Path
        # e.g., "/dev/sda1 • ext4 • Samsung SSD 850"
        extras = [path]
        if fstype: extras.append(fstype)
        if dev.get('model'): extras.append(dev.get('model'))
        subtitle = " • ".join([str(x) for x in extras if x])

        # 4. Create Row
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_icon_name(icon_name) # Requires Adw 1.3+ for set_icon_name, older use add_prefix
        
        # Fallback for older Adwaita regarding icon
        # We manually add a prefix icon to be safe/customizable
        icon = Gtk.Image.new_from_icon_name(icon_name)
        # If unsafe, maybe a warning badge?
        if not is_safe:
             icon.add_css_class("warning") # or specific color style
        row.add_prefix(icon)

        # 5. Selection Button
        btn = Gtk.Button(label="Select")
        btn.set_valign(Gtk.Align.CENTER)
        
        if is_safe:
            btn.add_css_class("suggested-action")
        else:
            btn.add_css_class("destructive-action")
            btn.set_label("Overwrite")
        
        btn.connect("clicked", self._on_selected, path)
        row.add_suffix(btn)
        
        # 6. Safety Label (Suffix)
        # If unsafe, show a small label explaining why
        if not is_safe:
            lbl = Gtk.Label(label=fstype or "In Use")
            lbl.add_css_class("dim-label")
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_margin_end(10)
            row.add_suffix(lbl)

        self.list_box.append(row)

    def _on_selected(self, btn, path):
        self.emit("device-selected", path)
        self.close()
