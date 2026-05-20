# main_window.py

import gi
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

# We ONLY import the StatusPage class.
from .status_page import StatusPage
from .configure_page import ConfigurePage
from .tune_page import TunePage
from .hibernate_page import HibernatePage
from .log_viewer import LogViewerDialog
from .global_config_dialog import GlobalConfigDialog

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(600, 700)
        self.set_title("Z-Manager")

        # Create a toolbar view as the primary window child
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        # Create header bar and add it to the top of the toolbar view
        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        # --- App Action Buttons (Logs & Settings) ---
        app_actions_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        
        logs_btn = Gtk.Button.new_from_icon_name("utilities-terminal-symbolic")
        logs_btn.add_css_class("flat")
        logs_btn.set_tooltip_text("View System Logs")
        logs_btn.connect("clicked", self.on_logs_clicked)
        app_actions_box.append(logs_btn)
        
        settings_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.set_tooltip_text("Global Settings")
        settings_btn.connect("clicked", self.on_settings_clicked)
        app_actions_box.append(settings_btn)
        
        header.pack_end(app_actions_box)

        # --- Navigation Button Box (Centered in the Title Bar) ---
        button_box = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        button_box.add_css_class("linked")

        # Status Button
        status_button = Gtk.ToggleButton()
        status_button.set_name("status")
        status_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        status_content.set_margin_start(15)
        status_content.set_margin_end(15)
        status_content.append(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        status_content.append(Gtk.Label(label="Status"))
        status_button.set_child(status_content)

        # Configure Button
        config_button = Gtk.ToggleButton()
        config_button.set_name("config")
        config_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        config_content.set_margin_start(15)
        config_content.set_margin_end(15)
        config_content.append(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        config_content.append(Gtk.Label(label="Configure"))
        config_button.set_child(config_content)
        
        # Tune Button
        tune_button = Gtk.ToggleButton()
        tune_button.set_name("tune")
        tune_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        tune_content.set_margin_start(15)
        tune_content.set_margin_end(15)
        tune_content.append(Gtk.Image.new_from_icon_name("tool-polygon-symbolic"))
        tune_content.append(Gtk.Label(label="Tune"))
        tune_button.set_child(tune_content)

        # Hibernate Button
        hibernate_button = Gtk.ToggleButton()
        hibernate_button.set_name("hibernate")
        hibernate_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        hibernate_content.set_margin_start(15)
        hibernate_content.set_margin_end(15)
        hibernate_content.append(Gtk.Image.new_from_icon_name("system-suspend-hibernate-symbolic"))
        hibernate_content.append(Gtk.Label(label="Hibernate"))
        hibernate_button.set_child(hibernate_content)

        # Manage Button Grouping
        config_button.set_group(status_button)
        tune_button.set_group(status_button)
        hibernate_button.set_group(status_button)
        status_button.set_active(True) 

        button_box.append(status_button)
        button_box.append(hibernate_button)
        button_box.append(tune_button)
        button_box.append(config_button)

        # Set as centered title widget of header bar
        header.set_title_widget(button_box)

        # --- Main content area using a Gtk.Stack ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        self.toolbar_view.set_content(self.stack)

        # Add pages to Gtk.Stack
        status_page = StatusPage()
        self.stack.add_named(status_page, "status")

        hibernate_page = HibernatePage()
        self.stack.add_named(hibernate_page, "hibernate")

        tune_page = TunePage()
        self.stack.add_named(tune_page, "tune")

        config_page = ConfigurePage()
        self.stack.add_named(config_page, "config")

        self.stack.set_visible_child_name("status")

        # Connect navigation handlers
        status_button.connect("toggled", self.on_nav_button_toggled)
        config_button.connect("toggled", self.on_nav_button_toggled)
        tune_button.connect("toggled", self.on_nav_button_toggled)
        hibernate_button.connect("toggled", self.on_nav_button_toggled)

        # Robust active page connection
        self.stack.connect("notify::visible-child", self.on_stack_visible_child_changed)

        self.load_css()
    
    def load_css(self):
        """Loads the application's CSS file."""
        provider = Gtk.CssProvider()
        
        # 1. Get the absolute path to this file's directory, then go up to the project root.
        css_path = Path(__file__).resolve().parent.parent / "css" / "style.css"
        # 2. Load the CSS from that absolute path.
        provider.load_from_path(str(css_path))
        
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )



    def on_nav_button_toggled(self, button: Gtk.ToggleButton):
        """
        Switches the visible page in the Gtk.Stack when tab is clicked.
        """
        if button.get_active():
            page_name = button.get_name()
            self.stack.set_visible_child_name(page_name)

    def on_stack_visible_child_changed(self, stack, pspec):
        """Triggered automatically when a new page is focused in the stack."""
        page = stack.get_visible_child()
        if page and hasattr(page, "lazy_load"):
            page.lazy_load()

    def on_logs_clicked(self, btn):
        """Opens the Log Viewer dialog."""
        dialog = LogViewerDialog(parent_window=self)
        dialog.present()

    def on_settings_clicked(self, btn):
        """Opens the Global Config dialog."""
        from core import config as zram_config
        current = zram_config.read_global_config()
        dialog = GlobalConfigDialog(parent=self, current_config=current)
        dialog.connect("applied", self._on_global_applied)
        dialog.present()

    def _on_global_applied(self, dialog):
        updates = dialog.updates
        from core.device_management import configurator
        res = configurator.apply_global_config(updates)
        
        # Simple feedback
        if res.success:
            print("Global settings applied.")
        else:
            print(f"Error applying global settings: {res.message}")

    def create_placeholder_page(self, text: str) -> Gtk.Widget:
        """
        Creates a simple placeholder widget for pages not yet implemented.
        """
        label = Gtk.Label(label=f"{text}\n(Not Implemented Yet)")
        label.set_vexpand(True)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.add_css_class("title-2")
        return label
