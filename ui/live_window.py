import sys
import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

from ui.live_orchestrator import apply_live_changes_generator, StepUpdate

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

.step-error {
    font-weight: bold;
    color: @error_color;
}
"""

class StepRow(Adw.ExpanderRow):
    """
    Enhanced Row:
    - Icon Stack for state (Pending/Running/Done/Error)
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

        # 4. Error
        img_error = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        img_error.add_css_class("error")
        self.icon_stack.add_named(img_error, "error")
        
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

    def set_state_done(self, success: bool = True):
        """Shows checkmark/error and collapses"""
        self.spinner.stop()
        self.remove_css_class("step-running")
        
        if success:
            self.icon_stack.set_visible_child_name("done")
            self.set_expanded(False) # Auto-collapse on success
        else:
            self.icon_stack.set_visible_child_name("error")
            self.add_css_class("step-error")
            self.set_expanded(True) # Keep expanded on error
            

    def update_status(self, human_readable_text):
        """Updates the subtitle (Human text)"""
        self.set_subtitle(human_readable_text)

    def append_raw_log(self, raw_text):
        """Appends to the terminal view (Raw text)"""
        buf = self.log_view.get_buffer()
        end_iter = buf.get_end_iter()
        buf.insert(end_iter, raw_text + "\n")
        
        # Auto-scroll
        adj = self.scrolled.get_vadjustment()
        GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))


class LiveModeWindow(Adw.Window):
    def __init__(self, changes, device_configs_snapshot, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Applying Configuration")
        self.set_default_size(600, 750)
        self.set_modal(True)
        
        self.changes = changes
        self.device_configs_snapshot = device_configs_snapshot
        self.current_row = None
        self.has_errors = False
        
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
        
        # Start Worker Thread
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        try:
            gen = apply_live_changes_generator(self.changes, self.device_configs_snapshot)
            for update in gen:
                GLib.idle_add(self._handle_update, update)
        except Exception as e:
            GLib.idle_add(self._handle_fatal_error, str(e))
        finally:
            GLib.idle_add(self.on_all_done)

    def _handle_update(self, update: StepUpdate):
        if update.type == "start_step":
            if self.current_row:
                pass
            row = StepRow(update.payload)
            self.group.add(row)
            row.set_state_running()
            self.current_row = row
            self.title_label.set_label(f"Running: {update.payload}")
            self.progress_bar.pulse()
            
        elif update.type == "log_line":
            if self.current_row:
                self.current_row.append_raw_log(update.payload)
                
        elif update.type == "step_done":
            if self.current_row:
                success, msg = update.payload
                self.current_row.set_state_done(success)
                self.current_row.update_status(msg)
                if not success:
                    self.has_errors = True

    def _handle_fatal_error(self, message: str):
        self.has_errors = True
        self.title_label.set_label("Fatal Error Occurred")
        row = StepRow("Critical System Error")
        self.group.add(row)
        row.append_raw_log(message)
        row.set_state_done(False)

    def on_all_done(self):
        self.progress_bar.set_fraction(1.0)
        
        if self.has_errors:
            self.title_label.set_label("Completed with Errors")
            self.title_label.add_css_class("error")
        else:
            self.title_label.set_label("Configuration Applied Successfully")
        
        self.header.set_show_end_title_buttons(True)
        self.header.set_show_start_title_buttons(True)

        btn_close = Gtk.Button(label="Close")
        if not self.has_errors:
            btn_close.add_css_class("suggested-action")
        else:
            btn_close.add_css_class("destructive-action")
            
        btn_close.connect("clicked", lambda x: self.close())
        self.header.pack_end(btn_close)

