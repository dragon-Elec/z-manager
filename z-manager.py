#!/usr/bin/env python3

import sys
import gi
import signal
from pathlib import Path
# Add the project root to the path to allow imports like `from core import ...`
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))



gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
from ui.main_window import MainWindow

class ZManagerApp(Adw.Application):
    """The main application class for Z-Manager."""
    def __init__(self, **kwargs):
        super().__init__(application_id="com.github.z-manager", **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        """Called when the application is activated."""
        # Create an instance of our main window
        win = MainWindow(application=app)
        # Present the window to the user
        win.present()

def main():
    # Allow Ctrl+C to kill the application
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = ZManagerApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
