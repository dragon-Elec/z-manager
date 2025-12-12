#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Gtk.Grid Showcase")
        self.set_default_size(400, -1) # -1 means auto-height

        # --- The Gtk.Grid Definition (from before) ---

        # 1. Create the main grid container.
        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=8,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )

        # 2. Create the widgets.
        header_label = Gtk.Label(
            label="Configuration Details",
            halign=Gtk.Align.START,
            css_classes=["title-4"] # Modern way to add style classes
        )
        key_algo = Gtk.Label(
            label="Algorithm",
            halign=Gtk.Align.END,
            css_classes=["dim-label"]
        )
        value_algo = Gtk.Label(
            label="zstd",
            halign=Gtk.Align.START,
            selectable=True,
            css_classes=["monospace"]
        )
        key_streams = Gtk.Label(
            label="Streams",
            halign=Gtk.Align.END,
            css_classes=["dim-label"]
        )
        value_streams = Gtk.Label(
            label="4",
            halign=Gtk.Align.START,
            selectable=True
        )
        key_writeback = Gtk.Label(
            label="Writeback",
            halign=Gtk.Align.END,
            css_classes=["dim-label"]
        )
        value_writeback = Gtk.LinkButton(
            uri="file:///dev/zram-writeback",
            label="/dev/zram-writeback",
            halign=Gtk.Align.START
        )
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        key_status = Gtk.Label(
            label="Active",
            halign=Gtk.Align.END,
            css_classes=["dim-label"]
        )
        value_status_switch = Gtk.Switch(
            active=True,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER
        )
        key_capacity = Gtk.Label(
            label="Capacity",
            halign=Gtk.Align.END,
            css_classes=["dim-label"]
        )
        value_capacity_bar = Gtk.ProgressBar(
            fraction=0.75,
            text="75% Full",
            show_text=True,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.CENTER
        )

        # 3. Attach all the widgets to the grid.
        row = 0
        grid.attach(header_label,      0, row, 2, 1)
        row += 1
        grid.attach(key_algo,          0, row, 1, 1)
        grid.attach(value_algo,        1, row, 1, 1)
        row += 1
        grid.attach(key_streams,       0, row, 1, 1)
        grid.attach(value_streams,     1, row, 1, 1)
        row += 1
        grid.attach(key_writeback,     0, row, 1, 1)
        grid.attach(value_writeback,   1, row, 1, 1)
        row += 1
        grid.attach(separator,         0, row, 2, 1)
        row += 1
        grid.attach(key_status,        0, row, 1, 1)
        grid.attach(value_status_switch, 1, row, 1, 1)
        row += 1
        grid.attach(key_capacity,      0, row, 1, 1)
        grid.attach(value_capacity_bar,1, row, 1, 1)

        # 4. 💡 CRITICAL STEP: Place the finished grid into the window.
        self.set_content(grid)


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


if __name__ == "__main__":
    app = MyApp(application_id="com.example.GridShowcase")
    app.run(sys.argv)