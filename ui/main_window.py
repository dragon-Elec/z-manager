# main_window.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

# We ONLY import the StatusPage class.
from .status_page import StatusPage

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

        # Manage Button Grouping
        config_button.set_group(status_button)
        tune_button.set_group(status_button)
        status_button.set_active(True) 

        button_box.append(status_button)
        button_box.append(tune_button)
        button_box.append(config_button)

        header.pack_start(button_box)

        # --- 2. NEW: Create custom window controls ---
        controls_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
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

        config_placeholder = self.create_placeholder_page("Configure Page")
        tune_placeholder = self.create_placeholder_page("Tune Page")
        
        self.stack.add_named(config_placeholder, "config")
        self.stack.add_named(tune_placeholder, "tune")

        self.stack.set_visible_child_name("status")

        status_button.connect("toggled", self.on_nav_button_toggled)
        config_button.connect("toggled", self.on_nav_button_toggled)
        tune_button.connect("toggled", self.on_nav_button_toggled)

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
        provider.load_from_path('css/style.css')
        
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