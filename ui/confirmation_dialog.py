import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, GObject, Gdk

class ConfirmationDialog(Adw.MessageDialog):
    """
    A GParted-style confirmation dialog showing:
    1. A summary list of actions (DELETE/CREATE/MODIFY).
    2. A "Terminal View" showing the exact diff of the config file.
    """
    
    def __init__(self, parent, changes, diff_text, **kwargs):
        super().__init__(**kwargs)
        
        self.set_transient_for(parent)
        self.set_heading("Confirm Configuration Changes")
        self.set_body("Review the pending changes before applying.")
        self.set_default_size(600, 500)
        
        # Load custom CSS for the terminal view (System Theme Aware)
        self._load_css()
        
        # Responses
        self.add_response("cancel", "Cancel")
        self.add_response("apply", "Apply")
        self.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        
        # Main Content Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # 1. Action Summary List
        header_lbl = Gtk.Label(label="Pending Operations", xalign=0)
        header_lbl.add_css_class("heading")
        main_box.append(header_lbl)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        
        for action, dev, _ in changes:
            row = Adw.ActionRow()
            
            if action == "DELETE":
                icon = "user-trash-symbolic"
                style = "error"
                lbl = f"Delete {dev}"
            elif action == "CREATE":
                icon = "list-add-symbolic"
                style = "success"
                lbl = f"Create {dev}"
            else:
                icon = "document-edit-symbolic"
                style = "accent"
                lbl = f"Modify {dev}"
                
            img = Gtk.Image.new_from_icon_name(icon)
            img.add_css_class(style)
            row.add_prefix(img)
            row.set_title(lbl)
            list_box.append(row)
            
        main_box.append(list_box)
        
        # 2. Diff View (Terminal Style)
        expander = Gtk.Expander()
        expander.set_label("Configuration Diff")
        expander.set_expanded(True)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_max_content_height(350)
        scrolled.set_propagate_natural_height(True)
        scrolled.add_css_class("view")
        
        self.text_view = Gtk.TextView()
        self.text_view.add_css_class("terminal-view") 
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        
        # Set Content
        self._setup_tags()
        self._set_diff_content(diff_text)
        
        scrolled.set_child(self.text_view)
        expander.set_child(scrolled)
        
        main_box.append(expander)
        
        self.set_extra_child(main_box)

    def _load_css(self):
        """Loads custom CSS for the terminal view."""
        # Use theme colors to respect Light/Dark mode automatically
        css = """
        .terminal-view {
            font-family: monospace;
            padding: 12px;
            background-color: @view_bg_color;
            color: @window_fg_color;
        }
        .terminal-view text {
            background-color: @view_bg_color;
            color: @window_fg_color;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _setup_tags(self):
        """
        Sets up tags with standard colors that work on both light and dark.
        """
        buf = self.text_view.get_buffer()
        
        # Green (Add) - Adwaita Green 4
        tag_add = buf.create_tag("add")
        c_add = Gdk.RGBA()
        c_add.parse("#2ec27e") 
        tag_add.set_property("foreground-rgba", c_add)

        # Red (Remove) - Adwaita Red 4
        tag_rm = buf.create_tag("remove")
        c_rm = Gdk.RGBA()
        c_rm.parse("#e01b24") 
        tag_rm.set_property("foreground-rgba", c_rm)
        
        # Blue (Header) - Adwaita Blue 4
        tag_hdr = buf.create_tag("header")
        c_hdr = Gdk.RGBA()
        c_hdr.parse("#1c71d8") 
        tag_hdr.set_property("foreground-rgba", c_hdr)
        tag_hdr.set_property("weight", Pango.Weight.BOLD)

    def _set_diff_content(self, diff_text):
        buffer = self.text_view.get_buffer()
        buffer.set_text("")
        
        for line in diff_text.splitlines(keepends=True):
            tag = None
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                 tag = "header"
            elif line.startswith("+"):
                 tag = "add"
            elif line.startswith("-"):
                 tag = "remove"
                 
            self._insert_with_tag(buffer, line, tag)
            
    def _insert_with_tag(self, buffer, text, tag_name):
        start = buffer.get_end_iter()
        buffer.insert(start, text)
        
        if tag_name:
            end = buffer.get_end_iter()
            # Calculate start of inserted text
            start = buffer.get_iter_at_offset(end.get_offset() - len(text.encode('utf-8')))
            # Approximation fix:
            start.backward_chars(len(text))
            buffer.apply_tag_by_name(tag_name, start, end)
