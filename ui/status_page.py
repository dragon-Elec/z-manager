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
    no_devices_label: Gtk.Label = Gtk.Template.Child()

    # Swap List group
    swap_list_group: Adw.PreferencesGroup = Gtk.Template.Child()

    # Event Log group
    event_log_container: Gtk.Box = Gtk.Template.Child()
    no_events_status_page: Gtk.Box = Gtk.Template.Child()
    no_events_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.no_devices_status_page.add_css_class("placeholder")
        self.no_events_status_page.add_css_class("placeholder")
        
        self._dynamic_device_rows = []
        self._dynamic_swap_rows = []
        
        self.refresh()

        GObject.timeout_add_seconds(30, self.refresh)

    def refresh(self):
        """Public method to refresh all data on the page."""
        self._populate_zram_devices()
        self._populate_swap_list()
        
        if not zdevice_ctl.list_devices():
            self.no_devices_status_page.set_visible(True)
        else:
            self.no_devices_status_page.set_visible(False)

    def _create_device_card(self, device: zdevice_ctl.DeviceInfo) -> Adw.PreferencesGroup:
        """Creates a 'card' for a single ZRAM device."""
        card = Adw.PreferencesGroup()

        # --- Main Action Row (Always Visible) ---
        usage_percent = 0
        try:
            disk_bytes = parse_size_to_bytes(device.disksize or '0')
            data_bytes = parse_size_to_bytes(device.data_size or '0')
            if disk_bytes > 0:
                usage_percent = int((data_bytes / disk_bytes) * 100)
        except (ValueError, ZeroDivisionError):
            usage_percent = 0

        subtitle = f"{usage_percent}% Used | {device.ratio or 'N/A'}x Ratio"
        
        main_row = Adw.ActionRow(title=device.name, subtitle=subtitle)
        
        usage_bar = Gtk.LevelBar(min_value=0, max_value=100, value=usage_percent, valign=Gtk.Align.CENTER)
        usage_bar.set_size_request(150, -1)
        main_row.add_suffix(usage_bar)
        
        card.add(main_row)

        # --- Expander Row for Details ---
        expander = Adw.ExpanderRow(title="Click to expand details")
        expander.set_subtitle(f"Disk Size: {device.disksize or 'N/A'} | Algorithm: {device.algorithm or 'N/A'}")
        
        details = {
            "Disk Size": device.disksize,
            "Compression Algorithm": device.algorithm,
            "Compressed Size": device.compr_size,
            "Uncompressed Data Size": device.data_size,
            "Streams": str(device.streams) if device.streams else "N/A",
            "Writeback Device": "(none)",
        }

        for title, value in details.items():
            row = Adw.ActionRow(title=title, subtitle=value or "N/A")
            expander.add_row(row)
            
        card.add(expander)
        
        return card

    def _populate_zram_devices(self):
        """Populates the list of active ZRAM devices with real-time stats."""
        for row in self._dynamic_device_rows:
            self.device_list_group.remove(row)
        self._dynamic_device_rows.clear()

        devices: List[zdevice_ctl.DeviceInfo] = zdevice_ctl.list_devices()

        if not devices:
            self.no_devices_status_page.set_visible(True)
            return

        self.no_devices_status_page.set_visible(False)

        for device in devices:
            new_card = self._create_device_card(device)
            self.device_list_group.add(new_card)
            self._dynamic_device_rows.append(new_card)

    def _populate_swap_list(self):
        """Populates the list of all system swap devices."""
        # You can keep or remove the print statement, it has served its purpose.
        # print(f"DEBUG: RAW DATA FROM health.get_all_swaps() -> {health.get_all_swaps()}")

        # 1. REMOVE the old rows we explicitly tracked from the last refresh.
        #    This is the logic that was missing.
        for row in self._dynamic_swap_rows:
            self.swap_list_group.remove(row)
        self._dynamic_swap_rows.clear()

        # 2. GET the latest, clean data from the backend.
        swaps: List[health.SwapDevice] = health.get_all_swaps()
        
        # 3. CREATE new rows and TRACK them for the next refresh.
        for swap in swaps:
            row = Adw.ActionRow()
            row.set_title(swap.name)
            size_hr = _kb_to_human(swap.size_kb)
            used_hr = _kb_to_human(swap.used_kb)
            subtitle = f"Size: {size_hr} | Used: {used_hr} | Priority: {swap.priority}"
            row.set_subtitle(subtitle)
            
            self.swap_list_group.add(row)
            # This is the crucial step: we add the new row to our tracking list.
            self._dynamic_swap_rows.append(row)

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
                ts_str = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                message = GLib.markup_escape_text(log_entry.message)
                label = Gtk.Label()
                label.set_markup(f"<small>{ts_str}</small>\n<b>{message}</b>")
                label.set_halign(Gtk.Align.START)
                label.set_wrap(True)

                icon_name = "dialog-information-symbolic"
                if log_entry.priority <= 3:
                    icon_name = "dialog-error-symbolic"
                elif log_entry.priority <= 4:
                    icon_name = "dialog-warning-symbolic"
                icon = Gtk.Image.new_from_icon_name(icon_name)

                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.append(icon)
                box.append(label)

                self.event_log_container.append(box).set_wrap(True)

                icon_name = "dialog-information-symbolic"
                if log_entry.priority <= 3:
                    icon_name = "dialog-error-symbolic"
                elif log_entry.priority <= 4:
                    icon_name = "dialog-warning-symbolic"
                icon = Gtk.Image.new_from_icon_name(icon_name)

                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.append(icon)
                box.append(label)

                self.event_log_container.append(box)