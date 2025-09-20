#!/usr/bin/env python3
# zman/ui/status_page.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

# --- Backend imports are kept for future use, but functions are not called ---
from core import health
from core import zdevice_ctl
from core.os_utils import parse_size_to_bytes
from modules import journal

import xml.etree.ElementTree as ET
import os
from typing import List

# Helper to get the absolute path to the .ui file
def get_ui_path(file_name: str) -> str:
    return os.path.join(os.path.dirname(__file__), file_name)

def _kb_to_human(size_kb: int) -> str:
    if not isinstance(size_kb, int):
        return ""
    if size_kb < 1024:
        return f"{size_kb} KiB"
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.1f} MiB"
    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GiB"


@Gtk.Template(filename=get_ui_path('status_page.ui'))
class StatusPage(Adw.Bin):
    # CRITICAL FIX: Name must match the 'class' attribute in the .ui file
    __gtype_name__ = 'StatusPage'


    # Device Status group
    device_list_group: Adw.PreferencesGroup = Gtk.Template.Child()
    no_devices_status_page: Gtk.Box = Gtk.Template.Child()
    # ✅ ADD THIS LINE
    no_devices_label: Gtk.Label = Gtk.Template.Child() 
    zram0_expander_template: Adw.ExpanderRow = Gtk.Template.Child()

    # Swap List group
    swap_list_group: Adw.PreferencesGroup = Gtk.Template.Child()

    # Event Log group
    event_log_container: Gtk.Box = Gtk.Template.Child()
    # 1. FIX: The type hint must match the UI file (it's a Gtk.Box)
    no_events_status_page: Gtk.Box = Gtk.Template.Child()
    # 2. NEW: Add a child for the label inside the box
    no_events_label: Gtk.Label = Gtk.Template.Child() # This will be added in the UI

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # --- THIS IS THE FIX ---
        # Force the CSS class onto the widgets at runtime to bypass the
        # AdwPreferencesGroup's interference with the UI file properties.
        self.no_devices_status_page.add_css_class("placeholder")
        self.no_events_status_page.add_css_class("placeholder")
        
        self._device_template_xml = self._get_device_template_xml()
        self.refresh()

        # Refresh the data every 30 seconds
        GObject.timeout_add_seconds(30, self.refresh)

    def refresh(self):
        """Public method to refresh all data on the page."""
        # --- TEMPORARILY DISABLED TO GET THE UI RUNNING ---
        # self._populate_zram_devices()
        # self._populate_swap_list()
        self._populate_event_log()
        
        # We can hide the template row to start with a clean slate
        self.zram0_expander_template.set_visible(False)
        self.no_devices_status_page.set_visible(True)
        

    def _get_device_template_xml(self) -> str | None:
        """
        Parses the UI file to extract the XML definition of the expander row template.
        This is used to dynamically create new device rows.
        """
        try:
            tree = ET.parse(get_ui_path('status_page.ui'))
            root = tree.getroot()
            template_node = root.find(".//*[@id='zram0_expander_template']")
            if template_node is not None:
                interface = ET.Element('interface')
                interface.append(template_node)
                return ET.tostring(interface, encoding='unicode')
        except (ET.ParseError, FileNotFoundError):
            return None
        return None


    def _populate_zram_devices(self):
        """Populates the list of active ZRAM devices with real-time stats."""
        for child in list(self.device_list_group):
            if child != self.zram0_expander_template and child != self.no_devices_status_page:
                self.device_list_group.remove(child)

        devices: List[zdevice_ctl.DeviceInfo] = zdevice_ctl.list_devices()

        if not devices:
            self.no_devices_status_page.set_visible(True)
            self.zram0_expander_template.set_visible(False)
            return

        self.no_devices_status_page.set_visible(False)
        if not self._device_template_xml:
            self.no_devices_status_page.set_visible(True)
            self.no_devices_status_page.set_title("UI Error")
            self.no_devices_status_page.set_description("Could not parse device template from UI file.")
            return

        for device in devices:
            builder = Gtk.Builder.new_from_string(self._device_template_xml, -1)
            new_row: Adw.ExpanderRow = builder.get_object("zram0_expander_template")
            new_row.set_title(device.name)
            usage_percent = 0
            try:
                disk_bytes = parse_size_to_bytes(device.disksize or '0')
                data_bytes = parse_size_to_bytes(device.data_size or '0')
                if disk_bytes > 0:
                    usage_percent = int((data_bytes / disk_bytes) * 100)
            except (ValueError, ZeroDivisionError):
                usage_percent = 0

            subtitle = f"{usage_percent}% Used | {device.ratio or 'N/A'}x Ratio"
            new_row.set_subtitle(subtitle)

            def get_widget(name):
                return builder.get_object(name)

            usage_bar: Gtk.LevelBar = get_widget("zram0_usage_bar")
            if usage_bar:
                usage_bar.set_value(usage_percent)
            details = {
                "zram0_disk_size_row": device.disksize,
                "zram0_algorithm_row": device.algorithm,
                "zram0_compr_size_row": device.compr_size,
                "zram0_data_size_row": device.data_size,
                "zram0_streams_row": str(device.streams) if device.streams else "N/A",
                "zram0_writeback_row": "(none)",
            }
            for name, value in details.items():
                row: Adw.ActionRow = get_widget(name)
                if row:
                    row.set_subtitle(value or "N/A")
            self.device_list_group.add(new_row)
        self.zram0_expander_template.set_visible(False)

    def _populate_swap_list(self):
        """Populates the list of all system swap devices."""
        child = self.swap_list_group.get_first_child()
        while child:
            self.swap_list_group.remove(child)
            child = self.swap_list_group.get_first_child()
        swaps: List[health.SwapDevice] = health.get_all_swaps()
        for swap in swaps:
            row = Adw.ActionRow()
            row.set_title(swap.name)
            size_hr = _kb_to_human(swap.size_kb)
            used_hr = _kb_to_human(swap.used_kb)
            subtitle = f"Size: {size_hr} | Used: {used_hr} | Priority: {swap.priority}"
            row.set_subtitle(subtitle)
            self.swap_list_group.add(row)

    def _populate_event_log(self):
        """Populates the System Health Events log."""
        for child in list(self.event_log_container):
            if child != self.no_events_status_page:
                self.event_log_container.remove(child)

        devices = zdevice_ctl.list_devices()
        all_logs: List[journal.JournalRecord] = []

        if not devices:
            self.no_events_status_page.set_visible(True)
            # 3. FIX: Use the correct widget and method
            self.no_events_label.set_label("No Active ZRAM Devices Found")
            return

        for device in devices:
            unit = f"systemd-zram-setup@{device.name}.service"
            all_logs.extend(journal.list_zram_logs(unit=unit, count=50))

        all_logs.sort(key=lambda r: r.timestamp, reverse=True)
        logs_to_display = all_logs[:25]

        if not logs_to_display:
            self.no_events_status_page.set_visible(True)
            # 4. FIX: Use the correct widget and method
            self.no_events_label.set_label("No Recent Issues Found")
        else:
            self.no_events_status_page.set_visible(False)
            for log_entry in logs_to_display:
                row = Adw.ActionRow()
                row.set_title(log_entry.message)
                ts_str = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                row.set_subtitle(ts_str)
                icon_name = "dialog-information-symbolic"
                if log_entry.priority <= 3:
                    icon_name = "dialog-error-symbolic"
                elif log_entry.priority <= 4:
                    icon_name = "dialog-warning-symbolic"
                icon = Gtk.Image.new_from_icon_name(icon_name)
                row.add_prefix(icon)
                self.event_log_container.append(row)