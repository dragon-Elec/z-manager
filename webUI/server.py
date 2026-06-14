import os
import sys

# Global fixes for WebKitGTK blur and fractional scaling issues on Linux:
# 1. Disable fractional scaling interpolation in GL renderer to keep rendering grid-aligned
os.environ["GDK_DEBUG"] = "gl-no-fractional"
# 2. Disable DMA-BUF renderer to bypass driver-specific compositing conflicts on Intel/NVIDIA
os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"

import subprocess
import time
import json
import threading
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gio, GLib, WebKit

class ZManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, app, sidecar_process):
        super().__init__(application=app, title="Z-Manager")
        self.set_default_size(1024, 768)
        self.sidecar_process = sidecar_process

        # Create WebKit WebView
        self.webview = WebKit.WebView()
        
        # Configure WebKit Settings
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(True) # Allow Web Inspector (Right click -> Inspect)
        settings.set_enable_write_console_messages_to_stdout(True) # Print console logs to terminal
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_smooth_scrolling(False) # Disable smooth scrolling to prevent fractional blur on WebKitGTK
        settings.set_zoom_text_only(False)
        self.webview.set_zoom_level(1.0)
        
        # Setup Script Message Handler
        manager = self.webview.get_user_content_manager()
        manager.connect("script-message-received::zmanager", self.on_script_message_received)
        manager.register_script_message_handler("zmanager", None)
        
        # Start sidecar stdout reader thread
        threading.Thread(target=self.read_sidecar_stdout, daemon=True).start()

        # Add WebView to Window
        self.set_child(self.webview)

        # Load the Svelte App
        self.load_frontend()

    def on_script_message_received(self, manager, js_result):
        # In WebKitGTK 6.0 GI bindings, the second argument is already a JSC.Value
        if not js_result.is_string():
            return
            
        message_str = js_result.to_string()
        
        # Write to sidecar's stdin
        stdin = self.sidecar_process.stdin
        if stdin:
            try:
                stdin.write((message_str + "\n").encode('utf-8'))
                stdin.flush()
            except Exception as e:
                print(f"[Shell] Failed to write to sidecar stdin: {e}")

    def read_sidecar_stdout(self):
        stdout = self.sidecar_process.stdout
        if not stdout:
            return
            
        for line in stdout:
            line_str = line.decode('utf-8').strip()
            if not line_str:
                continue
                
            try:
                data = json.loads(line_str)
            except json.JSONDecodeError:
                # Log non-JSON output from the sidecar
                print(f"[Sidecar Output] {line_str}")
                continue
                
            GLib.idle_add(self.evaluate_message_in_webview, data)

    def evaluate_message_in_webview(self, data):
        js_code = f"if (window.onPythonMessage) window.onPythonMessage({json.dumps(data)});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def load_frontend(self):
        # Resolve path to webUI/dist/index.html
        script_dir = Path(__file__).parent.resolve()
        dist_dir = script_dir / "dist"
        index_file = dist_dir / "index.html"

        # Check if we are in dev mode (e.g., if Vite dev server is running)
        dev_mode = os.environ.get("ZMAN_DEV") == "1"
        
        if dev_mode:
            print("[Shell] Loading frontend from dev server: http://localhost:5173")
            self.webview.load_uri("http://localhost:5173")
        elif index_file.exists():
            file_uri = index_file.as_uri()
            print(f"[Shell] Loading frontend from local build: {file_uri}")
            self.webview.load_uri(file_uri)
        else:
            html = "<h1>Error: Frontend not built</h1><p>Run <code>pnpm build</code> in the webUI directory.</p>"
            self.webview.load_html(html, "localhost")

class ZManagerApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.zmanager.app", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.sidecar_process = None

    def do_activate(self):
        # Start the sidecar process
        script_dir = Path(__file__).parent.resolve()
        sidecar_path = script_dir / "sidecar.py"
        
        print(f"[Shell] Starting sidecar process via stdin/stdout: {sidecar_path}")
        self.sidecar_process = subprocess.Popen(
            [sys.executable, str(sidecar_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        
        win = self.props.active_window
        if not win:
            win = ZManagerWindow(self, self.sidecar_process)
        win.present()

    def do_shutdown(self):
        # Kill the sidecar process on exit
        if self.sidecar_process:
            print("[Shell] Killing sidecar process")
            self.sidecar_process.terminate()
            try:
                self.sidecar_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.sidecar_process.kill()
        Gtk.Application.do_shutdown(self)

def main():
    app = ZManagerApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
