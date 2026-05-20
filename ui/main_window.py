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

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(600, 700)
        self.set_title("Z-Manager")

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        # --- 1. Disable the default, integrated window buttons ---
        header.set_show_title_buttons(False)

        # --- Navigation Button Box (No changes here) ---
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

        header.pack_start(button_box)

        # --- NEW: App Action Buttons (Logs & Settings) ---
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

        # --- 2. NEW: Create custom window controls ---
        controls_box = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        controls_box.add_css_class("linked") # Optional, but can look nice

        # Minimize Button
        minimize_button = Gtk.Button.new_from_icon_name("window-minimize-symbolic")
        minimize_button.add_css_class("flat")
        minimize_button.connect("clicked", lambda btn: self.minimize())
        
        # Maximize/Restore Button
        self.maximize_button = Gtk.Button.new_from_icon_name("window-maximize-symbolic")
        self.maximize_button.add_css_class("flat")
        self.maximize_button.connect("clicked", self.on_maximize_toggle)
        self.connect("notify::maximized", self.on_window_state_change)

        # Close Button
        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.add_css_class("error") # Gives it the red hover effect
        close_button.add_css_class("window-close-button") # Add this new class
        close_button.connect("clicked", lambda btn: self.close())

        controls_box.append(minimize_button)
        controls_box.append(self.maximize_button)
        controls_box.append(close_button)

        # --- 3. NEW: Pack the custom controls to the end (right side) ---
        header.pack_end(controls_box)

        # --- Main content area using a Gtk.Stack (No changes here) ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.set_child(self.stack)

        status_page = StatusPage()
        self.stack.add_named(status_page, "status")

        config_page = ConfigurePage()
        tune_page = TunePage()
        hibernate_page = HibernatePage()
        
        self.stack.add_named(config_page, "config")
        self.stack.add_named(tune_page, "tune")
        self.stack.add_named(hibernate_page, "hibernate")

        self.stack.set_visible_child_name("status")

        status_button.connect("toggled", self.on_nav_button_toggled)
        config_button.connect("toggled", self.on_nav_button_toggled)
        tune_button.connect("toggled", self.on_nav_button_toggled)
        hibernate_button.connect("toggled", self.on_nav_button_toggled)

        # Set the initial icon state correctly when the app starts
        self.on_window_state_change()

        self.load_css()
    
    def on_maximize_toggle(self, button):
        """Toggles the window between maximized and unmaximized states."""
        # This method now ONLY changes the state. The icon is handled by the signal.
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()

    def on_window_state_change(self, *args):
        """Updates the maximize/restore icon based on the window's actual state."""
        # This method now handles the icon update.
        if self.is_maximized():
            self.maximize_button.set_icon_name("window-restore-symbolic")
        else:
            self.maximize_button.set_icon_name("window-maximize-symbolic")

    def load_css(self):
        """Loads the application's CSS file."""
        provider = Gtk.CssProvider()
        
        # --- THIS IS THE FIX ---
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
        A single, robust handler for all navigation buttons.
        It switches the visible page in the Gtk.Stack.
        """
        if button.get_active():
            page_name = button.get_name()
            self.stack.set_visible_child_name(page_name)
            
            # Lazy loading trigger
            page = self.stack.get_visible_child()
            if hasattr(page, "lazy_load"):
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
