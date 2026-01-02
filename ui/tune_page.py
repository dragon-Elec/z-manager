#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

import os

def get_ui_path(file_name):
    return os.path.join(os.path.dirname(__file__), file_name)

@Gtk.Template(filename=get_ui_path('tune_page.ui'))
class TunePage(Adw.Bin):
    """
    The page for tuning system kernel parameters related to ZRAM performance.
    This class is the Python backend for the tune_page.ui template.
    """
    __gtype_name__ = 'TunePage'

    def __init__(self, **kwargs):
        """Initializes the TunePage widget."""
        super().__init__(**kwargs)
