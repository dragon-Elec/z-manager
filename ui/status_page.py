# zman/ui/status_page.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

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
class StatusHealthPage(Adw.PreferencesPage):
    __gtype_name__ = 'StatusHealthPage'

    # Health Alerts group
    zswap_warning_banner: Adw.Banner = Gtk.Template.Child()
    disable_zswap_row: Adw.ActionRow = Gtk.Template.Child()
    zswap_status_icon: Gtk.Image = Gtk.Template.Child()
    disable_zswap_button: Gtk.Button = Gtk.Template.Child()

    # Device Status group
    device_list_group: Adw.PreferencesGroup = Gtk.Template.Child()
    no_devices_status_page: Adw.StatusPage = Gtk.Template.Child()
    zram0_expander_template: Adw.ExpanderRow = Gtk.Template.Child()

    # Swap List group
    swap_list_group: Adw.PreferencesGroup = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._device_template_xml = self._get_device_template_xml()
        self.refresh()

    def refresh(self):
        """Public method to refresh all data on the page."""
        self._populate_health_alerts()
        self._populate_zram_devices()
        self._populate_swap_list()

    def _get_device_template_xml(self) -> str | None:
        """
        Parses the UI file to extract the XML definition of the expander row template.
        This is used to dynamically create new device rows.
        """
        try:
            tree = ET.parse(get_ui_path('status_page.ui'))
            root = tree.getroot()
            # Use XPath to find the template by its ID
            template_node = root.find(".//*[@id='zram0_expander_template']")
            if template_node is not None:
                # We need to wrap the node in an <interface> tag for the builder
                interface = ET.Element('interface')
                interface.append(template_node)
                return ET.tostring(interface, encoding='unicode')
        except (ET.ParseError, FileNotFoundError):
            return None
        return None

    def _populate_health_alerts(self):
        """Checks for system health issues and updates the UI accordingly."""
        self.zswap_warning_banner.set_revealed(False)
        status = health.get_zswap_status()

        if status.enabled:
            self.disable_zswap_row.set_subtitle("ZSwap is active and may conflict with ZRAM.")
            self.zswap_status_icon.set_from_icon_name("dialog-warning-symbolic")
            self.disable_zswap_button.set_visible(True)
        else:
            self.disable_zswap_row.set_subtitle("ZSwap is correctly disabled.")
            self.zswap_status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.disable_zswap_button.set_visible(False)

    def _populate_zram_devices(self):
        """Populates the list of active ZRAM devices with real-time stats."""
        # 1. Clear existing device rows safely
        for child in list(self.device_list_group):
            if child != self.zram0_expander_template and child != self.no_devices_status_page:
                self.device_list_group.remove(child)

        devices: List[zdevice_ctl.DeviceInfo] = zdevice_ctl.list_devices()

        # 3. If no devices, show status page and hide template
        if not devices:
            self.no_devices_status_page.set_visible(True)
            self.zram0_expander_template.set_visible(False)
            return

        # 4. If devices exist, hide status page and populate list
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
                "zram0_writeback_row": "(none)",  # Placeholder
            }
            for name, value in details.items():
                row: Adw.ActionRow = get_widget(name)
                if row:
                    row.set_subtitle(value or "N/A")

            self.device_list_group.add(new_row)

        self.zram0_expander_template.set_visible(False)

    def _populate_swap_list(self):
        """Populates the list of all system swap devices."""
        # 2. Get the group and remove all children
        child = self.swap_list_group.get_first_child()
        while child:
            self.swap_list_group.remove(child)
            child = self.swap_list_group.get_first_child()

        # 1. Get swap devices
        swaps: List[health.SwapDevice] = health.get_all_swaps()

        # 3. Iterate and create rows
        for swap in swaps:
            # a. Create a new Adw.ActionRow
            row = Adw.ActionRow()

            # b. Set title
            row.set_title(swap.name)

            # c. Convert sizes to human-readable format
            size_hr = _kb_to_human(swap.size_kb)
            used_hr = _kb_to_human(swap.used_kb)

            # d. Set subtitle
            subtitle = f"Size: {size_hr} | Used: {used_hr} | Priority: {swap.priority}"
            row.set_subtitle(subtitle)

            # e. Add to the group
            self.swap_list_group.add(row)

    def _populate_event_log(self):
        """Populates the System Health Events log."""
        # Clear the container, keeping the status page
        while (child := self.event_log_container.get_first_child()):
            if child == self.no_events_status_page:
                break  # Stop if we hit the status page
            self.event_log_container.remove(child)

        devices = zdevice_ctl.list_devices()
        all_logs: List[journal.JournalRecord] = []

        if not devices:
            self.no_events_status_page.set_visible(True)
            self.no_events_status_page.set_title("No Active ZRAM Devices")
            self.no_events_status_page.set_description("Logs are not available because no ZRAM devices were found.")
            return

        for device in devices:
            unit = f"systemd-zram-setup@{device.name}.service"
            all_logs.extend(journal.list_zram_logs(unit=unit, count=50))

        # Sort all collected logs by timestamp, newest first
        all_logs.sort(key=lambda r: r.timestamp, reverse=True)

        # Limit to the most recent 25 entries overall
        logs_to_display = all_logs[:25]

        if not logs_to_display:
            self.no_events_status_page.set_visible(True)
            self.no_events_status_page.set_title("No Issues Found")
            self.no_events_status_page.set_description("The system journal contains no recent warnings or errors for ZRAM services.")
        else:
            self.no_events_status_page.set_visible(False)
            for log_entry in logs_to_display:
                row = Adw.ActionRow()
                row.set_title(log_entry.message)

                # Format timestamp for subtitle
                ts_str = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                row.set_subtitle(ts_str)

                # Add an icon based on log priority
                icon_name = "dialog-information-symbolic"
                if log_entry.priority <= 3: # Error
                    icon_name = "dialog-error-symbolic"
                elif log_entry.priority <= 4: # Warning
                    icon_name = "dialog-warning-symbolic"

                icon = Gtk.Image.new_from_icon_name(icon_name)
                row.add_prefix(icon)

                self.event_log_container.append(row)
