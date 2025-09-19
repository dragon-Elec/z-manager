#!/usr/bin/env python3
# test_css.py (Corrected)

import gi
import sys

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

# The CSS we want to apply, embedded as a string to avoid file path issues.
CSS = """
box.placeholder image {
  -gtk-icon-size: 20px;
  opacity: 0.5;
}

box.placeholder label {
  font-size: 50px;
  opacity: 0.8;
  font-weight: bold;
}
"""

class TestApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.TestCSS")
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        # 1. Load CSS
        provider = Gtk.CssProvider()

        # --- THIS IS THE FIX ---
        # The method expects a string, and passing -1 for the length tells it
        # to read the entire string.
        provider.load_from_data(CSS, -1)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # 2. Create Window and Widgets
        win = Gtk.ApplicationWindow(application=app, title="CSS Test")
        win.set_default_size(400, 300)

        # Create the box that will hold our content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        # THIS IS THE METHOD WE ARE TESTING
        box.add_css_class("placeholder")

        # Create the image and label
        image = Gtk.Image.new_from_icon_name("drive-multidisk-symbolic")
        label = Gtk.Label(label="Does this text look big?")

        # Add them to the box
        box.append(image)
        box.append(label)

        # Add the box to the window
        win.set_child(box)
        win.present()

if __name__ == "__main__":
    app = TestApp()
    sys.exit(app.run(sys.argv))