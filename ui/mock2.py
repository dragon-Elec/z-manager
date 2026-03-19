#!/usr/bin/env python3
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject, Gdk

# --- CSS (Kept exactly as you liked it) ---
CSS = """
.terminal-frame {
    background-color: alpha(currentColor, 0.05);
    border-radius: 8px;
    padding: 6px;
    margin: 6px 12px 12px 12px;
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
    Enhanced Row:
    - Icon Stack for state (Pending/Running/Done)
    - Terminal View for RAW logs
    - Dynamic Subtitle for "Human Readable" status
    """
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.set_title(title)
        self.set_subtitle("Pending")
        
        # --- Icon Stack ---
        self.icon_stack = Gtk.Stack()
        self.icon_stack.set_valign(Gtk.Align.CENTER)
        
        # 1. Pending
        img_pending = Gtk.Image.new_from_icon_name("media-record-symbolic")
        img_pending.set_opacity(0.3)
        self.icon_stack.add_named(img_pending, "pending")
        
        # 2. Running
        self.spinner = Gtk.Spinner()
        self.icon_stack.add_named(self.spinner, "running")
        
        # 3. Done
        img_done = Gtk.Image.new_from_icon_name("object-select-symbolic")
        img_done.add_css_class("success")
        self.icon_stack.add_named(img_done, "done")
        
        self.add_prefix(self.icon_stack)
        self.icon_stack.set_visible_child_name("pending")

        # --- Log View (Raw Stderr) ---
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("terminal-text")
        # Tight margins for terminal look
        self.log_view.set_bottom_margin(6)
        self.log_view.set_top_margin(6)
        self.log_view.set_left_margin(6)
        self.log_view.set_right_margin(6)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_min_content_height(80)
        self.scrolled.set_max_content_height(250)
        self.scrolled.set_propagate_natural_height(True)
        self.scrolled.add_css_class("terminal-frame")
        self.scrolled.set_child(self.log_view)
        
        self.add_row(self.scrolled)

    def set_state_running(self):
        """Activates the spinner and expands the row"""
        self.icon_stack.set_visible_child_name("running")
        self.spinner.start()
        self.add_css_class("step-running")
        self.set_expanded(True)

    def set_state_done(self):
        """Shows checkmark and collapses"""
        self.icon_stack.set_visible_child_name("done")
        self.spinner.stop()
        self.remove_css_class("step-running")
        self.set_subtitle("Completed") 
        self.set_expanded(False)

    def update_status(self, human_readable_text):
        """Updates the subtitle (Human text)"""
        self.set_subtitle(human_readable_text)

    def append_raw_log(self, raw_text):
        """Appends to the terminal view (Raw text)"""
        buf = self.log_view.get_buffer()
        end_iter = buf.get_end_iter()
        # Add timestamp for extra 'raw' feel? Optional.
        # buf.insert(end_iter, f"[{time.time()}] {raw_text}\n")
        buf.insert(end_iter, raw_text + "\n")
        
        # Auto-scroll
        adj = self.scrolled.get_vadjustment()
        GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))


class LiveModeWindow(Adw.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Applying Configuration")
        self.set_default_size(600, 750)
        
        # Load CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Layout
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        self.header = Adw.HeaderBar()
        # We hide these initially so the user doesn't kill the app 
        # while it's writing to system files.
        self.header.set_show_end_title_buttons(False) 
        self.header.set_show_start_title_buttons(False)
        
        toolbar_view.add_top_bar(self.header)

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

        # Header Info
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.title_label = Gtk.Label(label="Initializing...", css_classes=["title-2"])
        self.title_label.set_halign(Gtk.Align.START)
        
        self.progress_bar = Gtk.ProgressBar()
        
        header_box.append(self.title_label)
        header_box.append(self.progress_bar)
        box.append(header_box)

        self.group = Adw.PreferencesGroup()
        box.append(self.group)

        # --- MOCK DATA STRUCTURE ---
        # Format: (Step Title, List of (Raw Log, Human Status))
        # This simulates your application logic passing two distinct strings.
        self.steps_data = [
             ("Stopping Services", [
                 ("sudo zramctl -r /dev/zram0", "Detaching zram0"),
                 ("sudo zramctl -r /dev/zram1", "Detaching zram1"),
                 ("swapoff -a", "Disabling swap")
             ]),
             ("Loading Modules", [
                 ("modprobe zram num_devices=2", "Loading kernel module"),
                 ("cat /sys/module/zram/parameters/num_devices", "Verifying parameters"),
                 ("sysctl -w vm.swappiness=100", "Setting swappiness")
             ]),
             ("Configuring zram0", [
                 ("zramctl -f", "Finding free device"),
                 ("echo 4294967296 > /sys/block/zram0/disksize", "Setting disk size (4GB)"),
                 ("echo zstd > /sys/block/zram0/comp_algorithm", "Setting algorithm to ZSTD"),
                 ("mkswap /dev/zram0", "Formatting swap partition"),
                 ("swapon /dev/zram0 -p 100", "Activating swap (Priority 100)")
             ]),
             ("Configuring zram1", [
                 ("zramctl -f", "Finding free device"),
                 ("echo 2147483648 > /sys/block/zram1/disksize", "Setting disk size (2GB)"),
                 ("echo lzo > /sys/block/zram1/comp_algorithm", "Setting algorithm to LZO"),
                 ("mkswap /dev/zram1", "Formatting swap partition"),
                 ("swapon /dev/zram1 -p 50", "Activating swap (Priority 50)")
             ]),
             ("Finalizing", [
                 ("systemctl daemon-reload", "Reloading systemd"),
                 ("notify-send 'Done'", "Sending notification"),
                 ("exit 0", "Cleaning up")
             ])
        ]
        
        self.rows = []
        for title, operations in self.steps_data:
            row = StepRow(title)
            self.group.add(row)
            self.rows.append({"widget": row, "ops": operations})

        self.current_step_idx = 0
        self.current_op_idx = 0
        
        GLib.timeout_add(600, self.simulation_tick)

    def simulation_tick(self):
        if self.current_step_idx >= len(self.rows):
            self.on_all_done()
            return False

        step_data = self.rows[self.current_step_idx]
        row = step_data["widget"]
        ops = step_data["ops"] # List of (raw, human)
        
        # Global Progress Calculation
        total_steps = len(self.rows)
        fraction = (self.current_step_idx / total_steps) + ((self.current_op_idx / len(ops)) / total_steps)
        self.progress_bar.set_fraction(fraction)
        
        # Update Header
        self.title_label.set_label(f"Step {self.current_step_idx + 1} of {total_steps}: {row.get_title()}")

        # Start of Step
        if self.current_op_idx == 0:
            row.set_state_running()

        # Process Operation
        if self.current_op_idx < len(ops):
            raw_log, human_status = ops[self.current_op_idx]
            
            # 1. Update the Row Subtitle (Human readable)
            row.update_status(human_status)
            
            # 2. Append to Terminal View (Raw execution)
            row.append_raw_log(raw_log)
            
            self.current_op_idx += 1
            return True 
        else:
            # Step Finished
            row.set_state_done()
            self.current_step_idx += 1
            self.current_op_idx = 0
            return True

    def on_all_done(self):
        self.progress_bar.set_fraction(1.0)
        self.title_label.set_label("Configuration Applied Successfully")
        
        # 1. Restore the window controls (Close/Max/Min)
        self.header.set_show_end_title_buttons(True)
        self.header.set_show_start_title_buttons(True)

        # 2. Add the big "Close" button
        btn_close = Gtk.Button(label="Close")
        btn_close.add_css_class("suggested-action")
        btn_close.connect("clicked", lambda x: self.close())
        
        # Now we use the stored reference self.header
        self.header.pack_end(btn_close)

class MockupApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.LiveModeRefined2", flags=0)

    def do_activate(self):
        win = LiveModeWindow(application=self)
        win.present()

if __name__ == "__main__":
    app = MockupApp()
    app.run(sys.argv)
