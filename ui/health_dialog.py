#!/usr/bin/env python3
# zman/ui/health_dialog.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from core import health
from ui.health_button import HealthState
from ui.log_viewer import LogViewerDialog

class HealthReportDialog(Adw.Window):
    """
    A dialog that displays detailed system health information.
    Shows all health checks, warnings, and provides quick action buttons.
    """
    
    def __init__(self, parent_window, health_report: health.HealthReport, **kwargs):
        super().__init__(**kwargs)
        
        self.set_transient_for(parent_window)
        self.set_modal(False) # Disable modal to prevent "symmetric resizing" (centering) behavior
        self.set_default_size(500, 600)
        self.set_title("System Health Report")
        
        self._health_report = health_report
        
        # Main content
        toolbar_view = Adw.ToolbarView()
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)
        
        # Content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Overall Status Summary
        self._add_status_group(content_box)
        
        # Health Checks Details
        self._add_checks_group(content_box)
        
        # Diagnostics (Logs)
        self._add_diagnostics_group(content_box)
        
        # System Information
        self._add_system_info_group(content_box)
        
        # Notes/Warnings
        if self._health_report.notes:
            self._add_notes_group(content_box)
        

        # Use Adw.Clamp to constrain content width for better readability
        # and to keep it centered regardless of window width.
        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        clamp.set_child(content_box)
        
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)
        
        self.set_content(toolbar_view)
    
    def _add_status_group(self, parent_box):
        """Adds the overall status summary."""
        # Using a compact custom box instead of Adw.StatusPage
        # to avoid nested scrolling issues and large default padding.
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_valign(Gtk.Align.CENTER)
        status_box.set_margin_top(24)
        status_box.set_margin_bottom(24)
        
        # Determine overall state
        state = self._determine_overall_state()
        
        icon_name = "dialog-information-symbolic"
        title = "Unknown Status"
        description = "System status check pending"
        css_class = ""

        if state == HealthState.HEALTHY:
            icon_name = "emblem-ok-symbolic"
            title = "System is Healthy"
            description = "All components are functioning normally"
            css_class = "success"
        elif state == HealthState.WARNING:
            icon_name = "dialog-warning-symbolic"
            title = "Attention Needed"
            description = "Some optimizations are recommended"
            css_class = "warning"
        else:
            icon_name = "dialog-error-symbolic"
            title = "Issues Detected"
            description = "Please review the details below"
            css_class = "error"

        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(64)
        if css_class:
            icon.add_css_class(css_class)
        status_box.append(icon)

        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-2")
        status_box.append(title_label)

        # Description
        desc_label = Gtk.Label(label=description)
        desc_label.add_css_class("body")
        desc_label.add_css_class("dim-label") # Optional, common for descriptions
        desc_label.set_wrap(True)
        desc_label.set_justify(Gtk.Justification.CENTER)
        status_box.append(desc_label)
        
        parent_box.append(status_box)
    
    def _add_checks_group(self, parent_box):
        """Adds individual health check results."""
        group = Adw.PreferencesGroup()
        group.set_title("Health Checks")
        
        # ZRAM Devices
        devices_row = Adw.ActionRow()
        devices_row.set_title("ZRAM Devices")
        devices_row.set_subtitle(self._health_report.devices_summary)
        devices_icon = Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if "active" in self._health_report.devices_summary.lower() 
            else "dialog-information-symbolic"
        )
        devices_row.add_prefix(devices_icon)
        group.add(devices_row)
        
        # Sysfs Access
        sysfs_row = Adw.ActionRow()
        sysfs_row.set_title("Sysfs Access")
        sysfs_row.set_subtitle("Available" if self._health_report.sysfs_root_accessible else "Not accessible")
        sysfs_icon = Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if self._health_report.sysfs_root_accessible 
            else "dialog-error-symbolic"
        )
        sysfs_row.add_prefix(sysfs_icon)
        group.add(sysfs_row)
        
        # ZSwap Status (Critical Check)
        zswap_row = Adw.ActionRow()
        zswap_row.set_title("ZSwap Conflict Check")
        
        if self._health_report.zswap.available and self._health_report.zswap.enabled:
            zswap_row.set_subtitle("⚠️ ZSwap is enabled - may interfere with ZRAM")
            zswap_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            
            # Add "Fix It" button
            fix_button = Gtk.Button(label="Fix It")
            fix_button.set_valign(Gtk.Align.CENTER)
            fix_button.add_css_class("suggested-action")
            fix_button.connect("clicked", self._on_fix_zswap_clicked)
            zswap_row.add_suffix(fix_button)
        else:
            zswap_row.set_subtitle("✓ ZSwap is disabled (recommended)")
            zswap_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        
        zswap_row.add_prefix(zswap_icon)
        group.add(zswap_row)
        
        # Systemd
        systemd_row = Adw.ActionRow()
        systemd_row.set_title("Systemd")
        systemd_row.set_subtitle("Available" if self._health_report.systemd_available else "Not found")
        systemd_icon = Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if self._health_report.systemd_available 
            else "dialog-warning-symbolic"
        )
        systemd_row.add_prefix(systemd_icon)
        group.add(systemd_row)
        
        # Journal Access
        journal_row = Adw.ActionRow()
        journal_row.set_title("Journal Access")
        journal_row.set_subtitle("Available" if self._health_report.journal_available else "Limited (python3-systemd recommended)")
        journal_icon = Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if self._health_report.journal_available 
            else "dialog-information-symbolic"
        )
        journal_row.add_prefix(journal_icon)
        group.add(journal_row)
        
        parent_box.append(group)

    def _add_diagnostics_group(self, parent_box):
        """Adds diagnostics tools (Logs)."""
        group = Adw.PreferencesGroup()
        group.set_title("Diagnostics")
        
        log_row = Adw.ActionRow()
        log_row.set_title("System Logs")
        log_row.set_subtitle("View raw zram-setup logs")
        log_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-script-symbolic"))
        
        view_btn = Gtk.Button(label="View Logs")
        view_btn.set_valign(Gtk.Align.CENTER)
        view_btn.connect("clicked", self._on_view_logs_clicked)
        
        log_row.add_suffix(view_btn)
        group.add(log_row)
        
        parent_box.append(group)
    
    def _add_system_info_group(self, parent_box):
        """Adds system information."""
        group = Adw.PreferencesGroup()
        group.set_title("System Information")
        
        kernel_row = Adw.ActionRow()
        kernel_row.set_title("Kernel Version")
        kernel_row.set_subtitle(self._health_report.kernel_version)
        group.add(kernel_row)
        
        parent_box.append(group)
    
    def _add_notes_group(self, parent_box):
        """Adds notes and warnings."""
        group = Adw.PreferencesGroup()
        group.set_title("Notes & Warnings")
        
        for note in self._health_report.notes:
            note_row = Adw.ActionRow()
            note_row.set_title(note)
            
            # Choose icon based on note severity
            if "conflict" in note.lower() or "enabled" in note.lower():
                icon_name = "dialog-warning-symbolic"
            elif "missing" in note.lower() or "not found" in note.lower():
                icon_name = "dialog-information-symbolic"
            else:
                icon_name = "dialog-information-symbolic"
            
            icon = Gtk.Image.new_from_icon_name(icon_name)
            note_row.add_prefix(icon)
            group.add(note_row)
        
        parent_box.append(group)
    
    def _determine_overall_state(self) -> HealthState:
        """Determines the overall health state from the report."""
        # Critical checks
        if not self._health_report.sysfs_root_accessible:
            return HealthState.ERROR
        
        # Warning checks
        if self._health_report.zswap.available and self._health_report.zswap.enabled:
            return HealthState.WARNING
        
        if not self._health_report.systemd_available:
            return HealthState.WARNING
        
        # All good
        return HealthState.HEALTHY
    
    def _on_fix_zswap_clicked(self, button):
        """Handles the 'Fix ZSwap' button click."""
        # TODO: Implement ZSwap fix logic (navigate to Tune page or apply fix)
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Fix ZSwap",
            body="This feature will navigate to the Tune page where you can disable ZSwap.\n\nFor now, please use the Tune page manually.",
        )
        dialog.add_response("ok", "OK")
        dialog.present()
    
    def _on_view_logs_clicked(self, button):
        """Opens the Log Viewer dialog."""
        dialog = LogViewerDialog(parent_window=self)
        dialog.present()
