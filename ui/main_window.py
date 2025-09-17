#!/usr/bin/env python3

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

        button_box = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        button_box.add_css_class("linked")

        # --- Status Button ---
        status_button = Gtk.ToggleButton()
        status_button.set_name("status") # Name is key for navigation
        status_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        status_content.set_margin_start(15)
        status_content.set_margin_end(15)
        status_content.append(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        status_content.append(Gtk.Label(label="Status"))
        status_button.set_child(status_content)
        # Signal connection moved to the end

        # --- Configure Button ---
        config_button = Gtk.ToggleButton()
        config_button.set_name("config") # Name is key for navigation
        config_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        config_content.set_margin_start(15)
        config_content.set_margin_end(15)
        config_content.append(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        config_content.append(Gtk.Label(label="Configure"))
        config_button.set_child(config_content)
        # Signal connection moved to the end
        
        # --- Tune Button ---
        tune_button = Gtk.ToggleButton()
        tune_button.set_name("tune") # Name is key for navigation
        tune_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        tune_content.set_margin_start(15)
        tune_content.set_margin_end(15)
        tune_content.append(Gtk.Image.new_from_icon_name("tool-polygon-symbolic"))
        tune_content.append(Gtk.Label(label="Tune"))
        tune_button.set_child(tune_content)
        # Signal connection moved to the end

        # --- Manage Button Grouping ---
        config_button.set_group(status_button)
        tune_button.set_group(status_button)
        
        # We start on the "Status" page.
        status_button.set_active(True) 

        button_box.append(status_button)
        button_box.append(tune_button)
        button_box.append(config_button)

        header.pack_start(button_box)

        # --- Main content area using a Gtk.Stack ---
        # This MUST be created before signals are connected.
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.set_child(self.stack)

        # --- Add the REAL StatusPage ---
        status_page = StatusPage()
        self.stack.add_named(status_page, "status")

        # --- Add PLACEHOLDERS for the other pages ---
        config_placeholder = self.create_placeholder_page("Configure Page")
        tune_placeholder = self.create_placeholder_page("Tune Page")
        
        self.stack.add_named(config_placeholder, "config")
        self.stack.add_named(tune_placeholder, "tune")

        # Set the initial visible page to match the active button
        self.stack.set_visible_child_name("status")

        # --- CRITICAL FIX: Connect signals AFTER self.stack is created ---
        status_button.connect("toggled", self.on_nav_button_toggled)
        config_button.connect("toggled", self.on_nav_button_toggled)
        tune_button.connect("toggled", self.on_nav_button_toggled)

        self.load_css()

    def load_css(self):
        """Loads the application's CSS file."""
        provider = Gtk.CssProvider()
        # Make sure the path to your style.css is correct
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
