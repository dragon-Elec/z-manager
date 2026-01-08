
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

class GlobalConfigDialog(Adw.Window):
    """
    A dialog to edit the [zram-generator] global section.
    """
    __gtype_name__ = 'GlobalConfigDialog'
    
    __gsignals__ = {
        'applied': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, parent=None, current_config=None):
        super().__init__(modal=True, transient_for=parent)
        self.set_default_size(450, 400)
        self.set_title("Global Settings")
        
        # Current Config (Dict)
        self.config = current_config or {}

        # Layout
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content)
        
        # Header
        header = Adw.HeaderBar()
        content.append(header)
        
        # Apply Button
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply_clicked)
        header.pack_end(apply_btn)
        
        # Preferences Page
        page = Adw.PreferencesPage()
        content.append(page)
        
        group = Adw.PreferencesGroup()
        group.set_title("System-Wide Defaults")
        group.set_description("These settings apply to automatically created devices that don't have specific overrides.")
        page.add(group)
        
        # 1. Default Algorithm
        self.algo_row = Adw.ComboRow()
        self.algo_row.set_title("Default Algorithm")
        self.algo_row.set_subtitle("compression-algorithm")
        
        model = Gtk.StringList()
        model.append("zstd (Default)")
        model.append("lzo-rle")
        model.append("lz4")
        self.algo_row.set_model(model)
        
        # Set current selection
        current_algo = self.config.get("compression-algorithm", "")
        if current_algo == "lzo-rle": self.algo_row.set_selected(1)
        elif current_algo == "lz4": self.algo_row.set_selected(2)
        else: self.algo_row.set_selected(0)

        group.add(self.algo_row)
        
        # 2. Default Size (Entry)
        self.size_row = Adw.EntryRow()
        self.size_row.set_title("Default Size")
        self.size_row.set_text(self.config.get("zram-size", ""))
        self.size_row.set_show_apply_button(False)
        group.add(self.size_row)
        
        # Note
        note = Gtk.Label(label="Note: Specific device sections will override these values.")
        note.add_css_class("caption")
        note.set_margin_top(12)
        note.set_wrap(True)
        note.set_justify(Gtk.Justification.CENTER)
        content.append(note)

    def _on_apply_clicked(self, btn):
        # Gather data
        updates = {}
        
        # Algo
        idx = self.algo_row.get_selected()
        algos = ["zstd", "lzo-rle", "lz4"]
        val = algos[idx]
        # Only save if different from default? 
        # Actually zram-generator default is zstd, so no need to save 'zstd' unless explicit
        if idx == 0:
            updates["compression-algorithm"] = None # Remove setting to use system default
        else:
            updates["compression-algorithm"] = val
            
        # Size
        size = self.size_row.get_text().strip()
        updates["zram-size"] = size if size else None
        
        self.updates = updates
        self.emit("applied")
        self.close()
