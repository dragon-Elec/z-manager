#!/usr/bin/env python3
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject, Gdk

# Modern CSS for the "Terminal" look
CSS = """
.terminal-frame {
    background-color: alpha(currentColor, 0.05);
    border-radius: 8px;
    padding: 6px;
    margin: 6px 12px 12px 12px; /* Top Right Bottom Left */
}

.terminal-text {
    font-family: 'Monospace';
    font-size: 11px;
}

.step-running {
    font-weight: bold;
    color: @accent_color;
}
"""

class StepRow(Adw.ExpanderRow):
    """
    A custom wrapper around ExpanderRow to handle state cleanly.
    """
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.set_title(title)
        self.set_subtitle("Pending")
        
        # --- State Icon Stack ---
        # We use a Stack to switch icons instantly without rebuilding widgets
        self.icon_stack = Gtk.Stack()
        self.icon_stack.set_valign(Gtk.Align.CENTER)
        
        # 1. Pending Icon (Dimmed Dot)
        img_pending = Gtk.Image.new_from_icon_name("media-record-symbolic")
        img_pending.set_opacity(0.3)
        self.icon_stack.add_named(img_pending, "pending")
        
        # 2. Running Icon (Spinner)
        self.spinner = Gtk.Spinner()
        self.icon_stack.add_named(self.spinner, "running")
        
        # 3. Done Icon (Checkmark)
        img_done = Gtk.Image.new_from_icon_name("object-select-symbolic")
        img_done.add_css_class("success")
        self.icon_stack.add_named(img_done, "done")
        
        self.add_prefix(self.icon_stack)
        self.icon_stack.set_visible_child_name("pending")

        # --- Log View (Terminal Style) ---
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("terminal-text")
        self.log_view.set_bottom_margin(6)
        self.log_view.set_top_margin(6)
        self.log_view.set_left_margin(6)
        self.log_view.set_right_margin(6)
        
        # Scrolled Window wrapper
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_min_content_height(80)
        self.scrolled.set_max_content_height(250)
        self.scrolled.set_propagate_natural_height(True)
        self.scrolled.add_css_class("terminal-frame") # Custom look
        self.scrolled.set_child(self.log_view)
        
        self.add_row(self.scrolled)

    def set_status(self, status):
        """Helper to switch states cleanly"""
        if status == "running":
            self.icon_stack.set_visible_child_name("running")
            self.spinner.start()
            self.set_subtitle("Processing...")
            self.add_css_class("step-running") # Highlight title
            self.set_expanded(True)
            
        elif status == "done":
            self.icon_stack.set_visible_child_name("done")
            self.spinner.stop()
            self.set_subtitle("Completed")
            self.remove_css_class("step-running")
            self.set_expanded(False)
            
        elif status == "pending":
            self.icon_stack.set_visible_child_name("pending")
            self.set_subtitle("Pending")

    def append_log(self, text):
        buf = self.log_view.get_buffer()
        end_iter = buf.get_end_iter()
        buf.insert(end_iter, text + "\n")
        
        # Auto-scroll logic
        adj = self.scrolled.get_vadjustment()
        GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))


class LiveModeWindow(Adw.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Applying Configuration")
        self.set_default_size(600, 750)
        
        # CSS Provider
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main Structure
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header Bar
        header = Adw.HeaderBar()
        # Add a "Cancel" button for realism (visually disabled for now)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.set_sensitive(False)
        header.pack_start(btn_cancel)
        toolbar_view.add_top_bar(header)

        # Content Container
        scrolled = Gtk.ScrolledWindow()
        toolbar_view.set_content(scrolled)

        clamp = Adw.Clamp(maximum_size=650)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(16)
        box.set_margin_end(16)
        clamp.set_child(box)

        # 1. Dynamic Header Area
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        self.title_label = Gtk.Label(label="Initializing...", css_classes=["title-2"])
        self.title_label.set_halign(Gtk.Align.START)
        
        # Global Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(False)
        
        header_box.append(self.title_label)
        header_box.append(self.progress_bar)
        box.append(header_box)

        # 2. The List
        self.group = Adw.PreferencesGroup()
        box.append(self.group)

        # Data & Initialization
        self.steps_data = [
             ("Stopping Services", ["Stopping zram0...", "Stopping zram1..."]),
             ("Loading Modules", ["modprobe zram", "Verifying kernel support..."]),
             ("Applying Defaults", ["Setting swappiness...", "Setting page-cluster..."]),
             ("Configuring zram0", ["Allocating 4GB...", "Compiling...", "Formatting swap...", " activating priority 100"]),
             ("Configuring zram1", ["Allocating 2GB...", "Compiling...", "Formatting swap...", " activating priority 50"]),
             ("Finalizing", ["Updating fstab...", "Notifying systemd...", "Done."])
        ]
        
        self.rows = []
        for title, logs in self.steps_data:
            row = StepRow(title)
            self.group.add(row)
            self.rows.append({"widget": row, "logs": logs})

        # Simulation State
        self.current_step_idx = 0
        self.current_log_idx = 0
        
        # Kick off
        GLib.timeout_add(500, self.simulation_tick)

    def simulation_tick(self):
        if self.current_step_idx >= len(self.rows):
            self.on_all_done()
            return False

        step_data = self.rows[self.current_step_idx]
        row = step_data["widget"]
        logs = step_data["logs"]
        
        # Update Global Progress
        total_steps = len(self.rows)
        fraction = (self.current_step_idx / total_steps) + ((self.current_log_idx / len(logs)) / total_steps)
        self.progress_bar.set_fraction(fraction)
        
        # Update Header Text
        self.title_label.set_label(f"Step {self.current_step_idx + 1} of {total_steps}: {row.get_title()}")

        # Start of Step
        if self.current_log_idx == 0:
            row.set_status("running")

        # Process Log
        if self.current_log_idx < len(logs):
            row.append_log(logs[self.current_log_idx])
            self.current_log_idx += 1
            # Variable speed for "realism"
            return True 
        else:
            # Step Finished
            row.set_status("done")
            self.current_step_idx += 1
            self.current_log_idx = 0
            return True

    def on_all_done(self):
        self.progress_bar.set_fraction(1.0)
        self.title_label.set_label("Configuration Applied Successfully")
        
        # Show a toast instead of a popup dialog (Less intrusive)
        toast = Adw.Toast.new("All operations completed.")
        toast.set_timeout(3000)
        
        # To add a toast in Adw.Window, we need an OverlaySplitView or similar, 
        # but Adw.ToolbarView supports add_toast in newer versions. 
        # For safety in standard GTK4/Adw1, we just change the UI state.
        
        # Change Cancel button to Close
        # (In a real app, you'd bind this button)

class MockupApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.LiveModeRefined", flags=0)

    def do_activate(self):
        win = LiveModeWindow(application=self)
        win.present()

if __name__ == "__main__":
    app = MockupApp()
    app.run(sys.argv)
