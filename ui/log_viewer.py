#!/usr/bin/env python3
# zman/ui/log_viewer.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, Gdk

from modules import journal
from core import zdevice_ctl

class LogViewerDialog(Adw.Window):
    """
    A dialog that displays raw system logs with bash-like syntax highlighting.
    """
    
    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs)
        
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_default_size(700, 500)
        self.set_title("System Logs")
        
        # Main layout
        toolbar_view = Adw.ToolbarView()
        
        # Header
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Refresh Button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh Logs")
        refresh_btn.connect("clicked", lambda x: self._load_logs())
        header.pack_start(refresh_btn)
        
        # Content Area - Mock Terminal
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Styling for "Terminal" look
        # We'll stick to Adwaita's dark theme if possible, but force some colors via tags
        self.buffer = self.text_view.get_buffer()
        self._create_tags()
        
        scrolled.set_child(self.text_view)
        
        # Add a custom CSS class to the TextView for background color if needed
        # But for consistency with system theme, standard widget background is usually fine.
        # Let's try to add a 'terminal' style class if we wanted, 
        # but for now we rely on TextTags for the "syntax highlighting".
        
        toolbar_view.set_content(scrolled)
        self.set_content(toolbar_view)
        
        self._load_logs()

    def _create_tags(self):
        """Creates GtkTextTags for syntax highlighting."""
        # Timestamp: Dimmed/Gray
        tag_ts = self.buffer.create_tag("timestamp", foreground="#9a9996") # Dim gray
        
        # Keywords
        self.buffer.create_tag("keyword", foreground="#62a0ea", weight=Pango.Weight.BOLD) # Blue
        self.buffer.create_tag("error", foreground="#f66151", weight=Pango.Weight.BOLD) # Red
        self.buffer.create_tag("warning", foreground="#e5a50a", weight=Pango.Weight.BOLD) # Yellow
        self.buffer.create_tag("success", foreground="#57e389", weight=Pango.Weight.BOLD) # Green
        self.buffer.create_tag("unit", foreground="#d3869b") # Purple-ish

    def _load_logs(self):
        """Fetches and displays logs."""
        self.buffer.set_text("")
        
        # Fetch logs for all ZRAM devices
        devices = zdevice_ctl.list_devices()
        all_logs = []
        
        # If no devices, try fetching generic setup logs
        if not devices:
             all_logs.extend(journal.list_zram_logs(unit="systemd-zram-setup@*.service", count=50))
        else:
            for device in devices:
                unit = f"systemd-zram-setup@{device.name}.service"
                all_logs.extend(journal.list_zram_logs(unit=unit, count=50))
        
        # Sort by timestamp
        all_logs.sort(key=lambda r: r.timestamp)
        
        if not all_logs:
            self._append_text("No logs found for zram-setup services.\n", "timestamp")
            return
            
        iter_end = self.buffer.get_end_iter()
        
        for record in all_logs:
            # Format: [TIMESTAMP] [LEVEL] MESSAGE
            
            # Timestamp
            ts_str = record.timestamp.strftime("%b %d %H:%M:%S")
            self._append_text(f"{ts_str} ", "timestamp")
            
            # Message Processing for Highlighting
            msg = record.message
            tags = []
            
            # Basic Priority Coloring
            if record.priority <= 3: # Error
                tags.append("error")
            elif record.priority == 4: # Warning
                tags.append("warning")
            
            # Content-based Highlighting (Bash-like)
            if "Active: active" in msg or "Activated swap" in msg:
                tags.append("success")
            elif "Failed" in msg or "Error" in msg:
                tags.append("error")
            
            self._append_text(f"{msg}\n", *tags)
            
    def _append_text(self, text, *tags):
        """Appends text with given tag names."""
        start = self.buffer.get_end_iter()
        self.buffer.insert(start, text)
        if tags:
            end = self.buffer.get_end_iter()
            # Re-get start iter because insert invalidates it
            start = self.buffer.get_iter_at_offset(end.get_offset() - len(text.encode('utf-8')))
            # Actually len in chars is safer for GtkTextIter
            start.backward_chars(len(text))
            
            for tag_name in tags:
                self.buffer.apply_tag_by_name(tag_name, start, end)
