#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

@Gtk.Template(filename='configure_page.ui')
class ConfigurePage(Adw.PreferencesPage):
    """
    The page for configuring ZRAM settings. This class is the Python
    backend for the configure_page.ui template.
    """
    __gtype_name__ = 'ConfigurePage'

    def __init__(self, **kwargs):
        """Initializes the ConfigurePage widget."""
        super().__init__(**kwargs)
