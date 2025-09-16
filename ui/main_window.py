#!/usr/bin/env python3

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(600, 250)
        self.set_title("Z-Manager")

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        button_box = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        button_box.add_css_class("linked")

        # --- Status Button ---
        status_button = Gtk.ToggleButton()
        status_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        # 💡 Set margins on the content box to create horizontal space
        status_content.set_margin_start(15)
        status_content.set_margin_end(15)
        status_content.append(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        status_content.append(Gtk.Label(label=" Status ")) # No extra spaces needed
        status_button.set_child(status_content)

        # --- Configure Button ---
        config_button = Gtk.ToggleButton()
        config_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        config_content.set_margin_start(15)
        config_content.set_margin_end(15)
        config_content.append(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        config_content.append(Gtk.Label(label="Configure"))
        config_button.set_child(config_content)
        
        # --- Tune Button ---
        tune_button = Gtk.ToggleButton()
        tune_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        tune_content.set_margin_start(15)
        tune_content.set_margin_end(15)
        tune_content.append(Gtk.Image.new_from_icon_name("tool-polygon-symbolic"))
        tune_content.append(Gtk.Label(label=" Tune  "))
        tune_button.set_child(tune_content)
        
        config_button.set_group(status_button)
        tune_button.set_group(status_button)
        config_button.set_active(True)

        button_box.append(status_button)
        button_box.append(config_button)
        button_box.append(tune_button)

        header.pack_start(button_box)

        # Placeholder for the main content area
        placeholder_label = Gtk.Label(label="Page content will appear here.")
        placeholder_label.set_vexpand(True)
        self.set_child(placeholder_label)