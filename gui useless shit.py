# zman/gui.py
import sys
import gi

# Specify the required GTK versions
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, GObject
from . import __version__, APP_ID
# Move to core as source of truth
from .core.devices import list_devices as core_list_devices, get_writeback_status as core_get_wb
from .core.journal import list_zram_logs as core_list_logs

# --- 1. The Data Object (Updated to match core models) ---
class ZramDeviceItem(GObject.Object):
    name = GObject.Property(type=str)
    algorithm = GObject.Property(type=str)
    disk_size = GObject.Property(type=str)
    data_size = GObject.Property(type=str)
    compr_size = GObject.Property(type=str)
    ratio = GObject.Property(type=str)
    streams = GObject.Property(type=str)

    def __init__(self, dev: dict):
        super().__init__()
        self.update_properties(dev)

    def update_properties(self, dev: dict):
        self.name = dev.get('name', 'N/A')
        self.algorithm = f"[{dev.get('algorithm', 'N/A')}]"
        self.disk_size = dev.get('disksize', 'N/A')
        self.data_size = dev.get('data-size', 'N/A')
        self.compr_size = dev.get('compr-size', 'N/A')
        self.ratio = dev.get('ratio', 'N/A')
        self.streams = f"{dev.get('streams', 'N/A')} streams"

def _map_core_device_to_dict(core_dev) -> dict:
    """
    Convert core.devices.DeviceInfo into the dict shape previously used by GUI.
    """
    return {
        "name": getattr(core_dev, "name", "unknown"),
        "disksize": getattr(core_dev, "disksize", None) or "N/A",
        "data-size": getattr(core_dev, "data_size", None) or "N/A",
        "compr-size": getattr(core_dev, "compr_size", None) or "N/A",
        "algorithm": getattr(core_dev, "algorithm", None) or "N/A",
        "streams": getattr(core_dev, "streams", None) if getattr(core_dev, "streams", None) is not None else "N/A",
        "ratio": getattr(core_dev, "ratio", None) or "N/A",
    }

# --- 2. The "Status" Page Widget (now sources from core) ---
class StatusPage(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model = Gio.ListStore(item_type=ZramDeviceItem)
        selection_model = Gtk.NoSelection(model=self.model)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.list_view = Gtk.ListView(model=selection_model, factory=factory)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.list_view)
        scrolled_window.set_vexpand(True)

        empty_page = Adw.StatusPage(
            title="No Active ZRAM Devices",
            description="ZRAM may not be configured or the kernel module is not loaded.",
            icon_name="drive-multidisk-symbolic"
        )

        self.stack = Gtk.Stack()
        self.stack.add_named(scrolled_window, "list")
        self.stack.add_named(empty_page, "empty")
        self.append(self.stack)

    def _on_factory_setup(self, factory, list_item):
        row = Adw.ActionRow()
        list_item.set_child(row)

    def _on_factory_bind(self, factory, list_item):
        row = list_item.get_child()
        item = list_item.get_item()

        title = f"{item.name} ({item.disk_size}) - {item.algorithm}"
        subtitle = (f"Data: {item.data_size} → {item.compr_size} "
                    f"(Ratio: {item.ratio}) | {item.streams}")

        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_activatable(False)

    def _fetch_devices_from_core(self) -> list[dict]:
        mapped: list[dict] = []
        try:
            for d in core_list_devices():
                mapped.append(_map_core_device_to_dict(d))
        except Exception:
            # In a GUI, prefer to fail softly
            mapped = []
        return mapped

    def update_status(self):
        """
        Fetches new data from core and intelligently updates the model in place.
        """
        devices = self._fetch_devices_from_core()

        new_devices_map = {dev['name']: dev for dev in devices}

        stale_indices = []
        for i, item in enumerate(self.model):
            if item.name not in new_devices_map:
                stale_indices.append(i)
            else:
                item.update_properties(new_devices_map[item.name])
                del new_devices_map[item.name]

        for i in sorted(stale_indices, reverse=True):
            self.model.remove(i)

        for dev_data in new_devices_map.values():
            self.model.append(ZramDeviceItem(dev=dev_data))

        if self.model.get_n_items() > 0:
            self.stack.set_visible_child_name("list")
        else:
            self.stack.set_visible_child_name("empty")


# --- 3. The Main Application Window (Unchanged) ---
class ZManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(850, 600)
        self.set_title("Z-Manager")

        view_stack = Adw.ViewStack()
        view_switcher = Adw.ViewSwitcher(stack=view_stack)
        header_bar = Adw.HeaderBar()
        header_bar.pack_end(view_switcher)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header_bar)
        view_stack.set_vexpand(True)
        main_box.append(view_stack)
        self.set_content(main_box)

        self.status_page = StatusPage()
        view_stack.add_titled_with_icon(self.status_page, "status", "Status", "system-run-symbolic")

        page_configure = Adw.StatusPage(
            icon_name="preferences-system-symbolic",
            title="Configure",
            description="The ZRAM configuration form will be here."
        )
        view_stack.add_titled_with_icon(page_configure, "configure", "Configure", "preferences-system-symbolic")

        page_tune = Adw.StatusPage(
            icon_name="emblem-synchronizing-symbolic",
            title="Tune",
            description="System performance tuning options will be here."
        )
        view_stack.add_titled_with_icon(page_tune, "tune", "Tune", "emblem-synchronizing-symbolic")

        GLib.timeout_add_seconds(2, self.update_data)
        self.update_data()

    def update_data(self) -> bool:
        self.status_page.update_status()
        return True

# --- 4. The Application Class (Unchanged) ---
class ZManagerApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.window = None
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        if not self.window:
            self.window = ZManagerWindow(application=self)
        self.window.present()

def run_gui():
    Adw.init()
    app = ZManagerApp()
    sys.exit(app.run(None))
