import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, Gdk, GObject
import difflib

class ConfirmationWindow(Adw.Window):
    """
    A compact, high-density confirmation window.
    Replaces Adw.MessageDialog to fix spacing/redundancy issues.
    """
    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, parent, changes, old_txt, new_txt, **kwargs):
        super().__init__(**kwargs)
        
        self.old_txt = old_txt
        self.new_txt = new_txt
        self.changes = changes
        
        # Window Setup
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(650, 500) # Slightly smaller, better utilized
        self.set_title("Confirm Changes")
        
        # --- 1. The Header Bar (Saves vertical space) ---
        header_bar = Adw.HeaderBar()
        self.set_content(None) # Clear default
        
        # Cancel Button (Top Left)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self._on_response("cancel"))
        header_bar.pack_start(btn_cancel)
        
        # Apply Button (Top Right - Suggested Action)
        btn_apply = Gtk.Button(label="Apply")
        btn_apply.add_css_class("suggested-action")
        btn_apply.connect("clicked", lambda x: self._on_response("apply"))
        header_bar.pack_end(btn_apply)

        # --- 2. Main Layout ---
        # We use a ToolbarView to handle the headerbar + content cleanly
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        
        # Main vertical container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # --- Part A: The Changes List (Compact) ---
        # A scrolled window for the list in case there are many changes
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_max_content_height(150) # Don't let list eat whole screen
        list_scroll.set_propagate_natural_height(True)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        list_box.set_margin_top(12)
        list_box.set_margin_start(12)
        list_box.set_margin_end(12)
        list_box.set_margin_bottom(6)
        
        for action, dev, _ in changes:
            row = Adw.ActionRow()
            # Compact row height
            row.set_size_request(-1, 40) 
            
            if action == "DELETE":
                icon, style, lbl = "user-trash-symbolic", "error", f"Delete {dev}"
            elif action == "CREATE":
                icon, style, lbl = "list-add-symbolic", "success", f"Create {dev}"
            else:
                icon, style, lbl = "document-edit-symbolic", "accent", f"Modify {dev}"
                
            img = Gtk.Image.new_from_icon_name(icon)
            img.add_css_class(style)
            row.add_prefix(img)
            row.set_title(lbl)
            list_box.append(row)
            
        list_scroll.set_child(list_box)
        main_box.append(list_scroll)

        # --- Part B: Diff Controls ---
        # A slim bar between list and diff
        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        control_box.set_margin_start(12)
        control_box.set_margin_end(12)
        control_box.set_margin_bottom(6)
        
        diff_label = Gtk.Label(label="Configuration Diff", xalign=0)
        diff_label.add_css_class("heading")
        diff_label.set_hexpand(True)
        
        # Toggle Switch
        self.full_file_switch = Gtk.Switch()
        self.full_file_switch.set_valign(Gtk.Align.CENTER)
        self.full_file_switch.connect("notify::active", self._on_toggle_full_diff)
        
        switch_label = Gtk.Label(label="Full File")
        switch_label.add_css_class("dim-label") # Make it subtle
        
        control_box.append(diff_label)
        control_box.append(switch_label)
        control_box.append(self.full_file_switch)
        
        main_box.append(control_box)

        # --- Part C: The Text View (Your Logic) ---
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True) # Fill remaining space
        scrolled.add_css_class("frame")
        # Remove margins from scrolled window so it touches window edges (cleaner look)
        # or keep small margin if you prefer "floating" look. 
        # Let's keep small margin to match top.
        scrolled.set_margin_start(12)
        scrolled.set_margin_end(12)
        scrolled.set_margin_bottom(12)
        
        self.text_view = Gtk.TextView()
        self.text_view.add_css_class("monospace")
        self.text_view.set_editable(False)
        self.text_view.set_left_margin(8)
        self.text_view.set_right_margin(8)
        self.text_view.set_top_margin(8)
        self.text_view.set_bottom_margin(8)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        
        self._setup_view_tags()
        self._update_diff_view(full=False)
        
        scrolled.set_child(self.text_view)
        main_box.append(scrolled)
        
        toolbar_view.set_content(main_box)
        self.set_content(toolbar_view)

    def _on_response(self, response_id):
        """Emits the custom signal and closes."""
        self.emit("response", response_id)
        self.close()

    # --- Your Original Diff Logic Below (Preserved) ---

    def _setup_view_tags(self):
        buf = self.text_view.get_buffer()
        
        def make_tag(name, color_str, weight=None):
            tag = buf.create_tag(name)
            if color_str:
                c = Gdk.RGBA()
                c.parse(color_str)
                tag.set_property("foreground-rgba", c)
            if weight:
                tag.set_property("weight", weight)
        
        make_tag("add", "#26a269") 
        make_tag("remove", "#c01c28") 
        make_tag("header", "#1c71d8", Pango.Weight.BOLD)

    def _on_toggle_full_diff(self, switch, param):
        self._update_diff_view(full=switch.get_active())

    def _update_diff_view(self, full: bool):
        buf = self.text_view.get_buffer()
        buf.set_text("")
        
        curr_lines = self.old_txt.splitlines(keepends=True)
        new_lines = self.new_txt.splitlines(keepends=True)
        
        if full:
            diff = difflib.unified_diff(
                curr_lines, new_lines, 
                fromfile='Current', tofile='New', 
                n=999999
            )
        else:
            diff = difflib.unified_diff(
                curr_lines, new_lines, 
                fromfile='Current', tofile='New', 
                n=3
            )
            
        text = "".join(diff)
        if not text.strip() and self.old_txt == self.new_txt:
            text = "No changes detected (Content identical)."
        
        for line in text.splitlines(keepends=True):
            tag = None
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                 tag = "header"
            elif line.startswith("+"):
                 tag = "add"
            elif line.startswith("-"):
                 tag = "remove"
            self._insert_with_tag(buf, line, tag)

    def _insert_with_tag(self, buffer, text, tag_name):
        start = buffer.get_end_iter()
        buffer.insert(start, text)
        if tag_name:
            end = buffer.get_end_iter()
            # Calculate start by backing up count chars
            count = len(text) # Python len is char count
            start = end.copy()
            start.backward_chars(count)
            buffer.apply_tag_by_name(tag_name, start, end)
