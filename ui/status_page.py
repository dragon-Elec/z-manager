#!/usr/bin/env python3
# zman/ui/status_page.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib

# --- Backend imports are kept for future use, but functions are not called ---
from core import health
from core import zdevice_ctl
from core.os_utils import parse_size_to_bytes
import psutil # Added for RAM calculation
from ui.custom_widgets import CircularWidget, MemoryTube
from ui.health_button import HealthStatusButton, HealthState
from ui.health_dialog import HealthReportDialog

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.no_devices_status_page.add_css_class("placeholder")
        
        # Reparent no_devices_status_page into device_list_group
        # This allows us to keep the group visible (for the health button)
        # while showing the placeholder content inside it.
        parent = self.no_devices_status_page.get_parent()
        if parent:
            parent.remove(self.no_devices_status_page)
        self.device_list_group.add(self.no_devices_status_page)
        
        self._dynamic_swap_rows = []
        self._device_widgets = {} # Map[name, CircularWidget]
        
        # Health Status Button
        self._health_button = HealthStatusButton()
        self._health_button.connect("clicked", self._on_health_button_clicked)
        
        # Add health button to the header of the device list group
        self.device_list_group.set_header_suffix(self._health_button)
        
        # [LAYOUT FIX] Use FlowBox for Cards
        self._device_flowbox = Gtk.FlowBox()
        self._device_flowbox.set_valign(Gtk.Align.START)
        self._device_flowbox.set_max_children_per_line(5) # Auto wrap
        self._device_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._device_flowbox.set_column_spacing(12)
        self._device_flowbox.set_row_spacing(12)
        self._device_flowbox.set_margin_start(12)
        self._device_flowbox.set_margin_end(12)
        self._device_flowbox.set_margin_top(12)
        self._device_flowbox.set_margin_bottom(12)
        
        # Add the FlowBox to the Group
        self.device_list_group.add(self._device_flowbox)
        
        # Optimize: Only run refresh loop when visible
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)
        self._timer_id = None

    def _on_map(self, widget):
        if self._timer_id is None:
            self.refresh()
            self._timer_id = GLib.timeout_add_seconds(1, self.refresh)

    def _on_unmap(self, widget):
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def refresh(self):
        """Public method to refresh all data on the page."""
        # Optimization: Fetch system RAM once per cycle
        try:
            ram_total = psutil.virtual_memory().total
        except:
            ram_total = 1 # Prevent div/0
            
        self._populate_zram_devices(ram_total)
        self._populate_swap_list()
        self._update_health_button()
        
        # Check coverage
        if not self._device_widgets:
            self.no_devices_status_page.set_visible(True)
        else:
            self.no_devices_status_page.set_visible(False)
            
        return True

    def _create_device_row(self, device: zdevice_ctl.DeviceInfo, ram_total: int) -> Gtk.Widget:
        """Creates a 'CircularWidget' card for a single ZRAM device."""
        
        # Parse Sizes safely
        try:
            disk_bytes = parse_size_to_bytes(device.disksize or '0')
            data_bytes = parse_size_to_bytes(device.data_size or '0')
            compr_bytes = parse_size_to_bytes(device.compr_size or '0')
        except (ValueError, ZeroDivisionError):
            disk_bytes, data_bytes, compr_bytes = 0, 0, 0

        # Backing Device / Writeback Logic
        backing_dev = None
        bd_used = 0
        bd_limit = 0
        try:
            wb_status = zdevice_ctl.get_writeback_status(device.name)
            if wb_status and wb_status.backing_dev and wb_status.backing_dev != "none":
                backing_dev = wb_status.backing_dev
                # Placeholder for BD limits if needed in future
                pass
        except Exception:
            pass

        # Identify if Swap
        is_swap = "SWAP" in (device.mountpoint or "") or "swap" in (device.type or "").lower()

        # Instantiate Widget
        widget = CircularWidget(
            device_name=device.name,
            algo=device.algorithm,
            used_bytes=data_bytes,
            total_bytes=disk_bytes,
            orig_bytes=data_bytes,
            compr_bytes=compr_bytes,
            physical_ram_total=ram_total,
            is_swap=is_swap,
            backing_dev=backing_dev,
            bd_used=bd_used,
            bd_limit=bd_limit
        )
        # Store metadata to detect structural changes (like backing dev)
        widget._start_backing_dev = backing_dev
        
        return widget

    def _populate_zram_devices(self, ram_total: int):
        """Populates the list of active ZRAM devices with real-time stats."""
        
        # Get current devices
        devices: List[zdevice_ctl.DeviceInfo] = zdevice_ctl.list_devices()
        current_names = set()

        if not devices:
            # Clear all
            for child in list(self._device_widgets.values()):
                self._device_flowbox.remove(child)
            self._device_widgets.clear()
            
            # Show placeholder, hide flowbox
            self.no_devices_status_page.set_visible(True)
            self._device_flowbox.set_visible(False)
            
            # Ensure group is visible so health button shows
            self.device_list_group.set_visible(True)
            return

        self.no_devices_status_page.set_visible(False)
        self._device_flowbox.set_visible(True)
        self.device_list_group.set_visible(True)

        for device in devices:
            current_names.add(device.name)
            
            # Parse stats
            try:
                disk_bytes = parse_size_to_bytes(device.disksize or '0')
                data_bytes = parse_size_to_bytes(device.data_size or '0')
                compr_bytes = parse_size_to_bytes(device.compr_size or '0')
            except:
                disk_bytes, data_bytes, compr_bytes = 0, 0, 0
            
            # Check if exists
            widget = self._device_widgets.get(device.name)
            
            if widget:
                # OPTIMIZATION: Update existing
                # Check for structural changes (e.g. backing dev changed)
                # For now assuming backing dev doesn't change on the fly without remove/add.
                
                widget.update(
                    used_bytes=data_bytes,
                    total_bytes=disk_bytes,
                    orig_bytes=data_bytes,
                    compr_bytes=compr_bytes,
                    physical_ram_total=ram_total
                )
            else:
                # Create new
                new_widget = self._create_device_row(device, ram_total)
                new_widget.set_hexpand(False)
                new_widget.set_vexpand(False)
                self._device_flowbox.append(new_widget)
                self._device_widgets[device.name] = new_widget

        # Remove stale widgets
        for name in list(self._device_widgets.keys()):
            if name not in current_names:
                w = self._device_widgets.pop(name)
                self._device_flowbox.remove(w)

    def _populate_swap_list(self):
        """Populates the list of all system swap devices."""
        # Get latest data
        swaps: List[health.SwapDevice] = health.get_all_swaps()
        
        # Map existing rows by name for reuse
        existing_rows = {row.get_title(): row for row in self._dynamic_swap_rows}
        seen_names = set()

        for swap in swaps:
            seen_names.add(swap.name)
            
            size_hr = _kb_to_human(swap.size_kb)
            used_hr = _kb_to_human(swap.used_kb)
            subtitle = f"Size: {size_hr}  •  Used: {used_hr}  •  Priority: {swap.priority}"
            
            if swap.name in existing_rows:
                # Update existing row
                existing_rows[swap.name].set_subtitle(subtitle)
            else:
                # Create new row
                row = Adw.ActionRow()
                row.set_title(swap.name)
                row.set_subtitle(subtitle)
                
                icon_name = "drive-harddisk-symbolic" if "/dev/zram" not in swap.name else "memory-symbolic"
                row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
                
                self.swap_list_group.add(row)
                self._dynamic_swap_rows.append(row)

        # Remove stale rows
        active_rows = []
        for row in self._dynamic_swap_rows:
            name = row.get_title()
            if name not in seen_names:
                self.swap_list_group.remove(row)
            else:
                active_rows.append(row)
        self._dynamic_swap_rows = active_rows

    def _update_health_button(self):
        """Updates the health button state based on current system health."""
        health_report = health.check_system_health()
        
        # Determine state
        if not health_report.sysfs_root_accessible:
            state = HealthState.ERROR
            subtitle = "Critical system access issue"
        elif health_report.zswap.available and health_report.zswap.enabled:
            state = HealthState.WARNING
            subtitle = "ZSwap conflict detected"
        elif not health_report.systemd_available:
            state = HealthState.WARNING
            subtitle = "Limited functionality"
        elif len(health_report.notes) > 0:
            state = HealthState.WARNING
            subtitle = f"{len(health_report.notes)} recommendation(s)"
        else:
            state = HealthState.HEALTHY
            subtitle = None
        
        self._health_button.set_state(state, subtitle)
        
        # Store report for dialog
        self._current_health_report = health_report
    
    def _on_health_button_clicked(self, button):
        """Opens the health report dialog when the button is clicked."""
        if hasattr(self, '_current_health_report'):
            dialog = HealthReportDialog(
                parent_window=self.get_root(),
                health_report=self._current_health_report
            )
            dialog.present()
        else:
            # Fallback: run health check now
            health_report = health.check_system_health()
            dialog = HealthReportDialog(
                parent_window=self.get_root(),
                health_report=health_report
            )
            dialog.present()