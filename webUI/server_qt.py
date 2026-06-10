import sys
import os
# Disable Chromium sandbox to prevent Trace/breakpoint trap (SIGTRAP) on Linux
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
sys.argv.append("--no-sandbox")

# Force OpenGL graphics API to prevent SIGTRAP on Intel/Mesa drivers
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)

import json
import subprocess
import threading
from PySide6.QtCore import QUrl, Qt, QObject, Signal
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript

class SidecarListener(QObject):
    message_received = Signal(str)
    stderr_received = Signal(str)

    def __init__(self, sidecar_process):
        super().__init__()
        self.sidecar_process = sidecar_process

    def start(self):
        threading.Thread(target=self.read_stdout, daemon=True).start()
        threading.Thread(target=self.read_stderr, daemon=True).start()

    def read_stdout(self):
        while True:
            line = self.sidecar_process.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8').strip()
            if line_str:
                self.message_received.emit(line_str)

    def read_stderr(self):
        while True:
            line = self.sidecar_process.stderr.readline()
            if not line:
                break
            line_str = line.decode('utf-8').strip()
            if line_str:
                self.stderr_received.emit(line_str)

class SidecarBridge(QWebEnginePage):
    def __init__(self, sidecar_process, parent=None):
        super().__init__(parent)
        self.sidecar_process = sidecar_process

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Intercept console messages starting with "ipc:"
        if message.startswith("ipc:"):
            payload_str = message[4:]
            try:
                # Write the message directly to the sidecar's stdin
                if self.sidecar_process and self.sidecar_process.stdin:
                    self.sidecar_process.stdin.write((payload_str + "\n").encode('utf-8'))
                    self.sidecar_process.stdin.flush()
            except Exception as e:
                sys.stderr.write(f"[Qt Shell] Error writing to sidecar stdin: {e}\n")
                sys.stderr.flush()
        else:
            # Print other console messages to stderr
            sys.stderr.write(f"[Console] {message}\n")
            sys.stderr.flush()

class MainWindow(QMainWindow):
    def __init__(self, dev_mode=False):
        super().__init__()
        self.setWindowTitle("Z-Manager (Qt)")
        self.resize(1024, 768)
        self.setMinimumSize(800, 600)

        # Resolve sidecar path
        self.sidecar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sidecar.py"))
        sys.stderr.write(f"[Qt Shell] Spawning sidecar at: {self.sidecar_path}\n")
        sys.stderr.flush()

        # Spawn the sidecar process in Stdio IPC mode (no --port argument)
        self.sidecar_process = subprocess.Popen(
            [sys.executable, self.sidecar_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Create the webview and custom page
        self.view = QWebEngineView(self)
        self.page = SidecarBridge(self.sidecar_process, self.view)
        self.view.setPage(self.page)
        self.setCentralWidget(self.view)

        # Inject WebKitGTK IPC mock script at page load
        # This maps window.webkit.messageHandlers.zmanager.postMessage to console.log("ipc:" + msg)
        ipc_mock_script = QWebEngineScript()
        ipc_mock_script.setSourceCode("""
            if (!window.webkit) {
                window.webkit = {
                    messageHandlers: {
                        zmanager: {
                            postMessage: function(msg) {
                                console.log("ipc:" + msg);
                            }
                        }
                    }
                };
            }
        """)
        ipc_mock_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        ipc_mock_script.setWorldId(QWebEngineScript.MainWorld)
        ipc_mock_script.setRunsOnSubFrames(True)
        self.view.page().profile().scripts().insert(ipc_mock_script)

        # Start background threads to read sidecar stdout and stderr via Qt Signals
        self.listener = SidecarListener(self.sidecar_process)
        self.listener.message_received.connect(self.handle_sidecar_message)
        self.listener.stderr_received.connect(self.handle_sidecar_stderr)
        self.listener.start()

        # Load the frontend
        if dev_mode:
            sys.stderr.write("[Qt Shell] Loading dev server at http://localhost:5173\n")
            sys.stderr.flush()
            self.view.load(QUrl("http://localhost:5173"))
        else:
            dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist", "index.html"))
            sys.stderr.write(f"[Qt Shell] Loading production build at {dist_path}\n")
            sys.stderr.flush()
            self.view.load(QUrl.fromLocalFile(dist_path))

    def handle_sidecar_message(self, message):
        # Escape backslashes and single quotes for JS injection
        escaped_line = message.replace('\\', '\\\\').replace("'", "\\'")
        js_code = f"if (window.onPythonMessage) {{ window.onPythonMessage({escaped_line}); }}"
        self.view.page().runJavaScript(js_code)

    def handle_sidecar_stderr(self, message):
        sys.stderr.write(f"[Sidecar Stderr] {message}\n")
        sys.stderr.flush()

    def closeEvent(self, event):
        # Clean up the sidecar process on exit
        sys.stderr.write("[Qt Shell] Shutting down sidecar process...\n")
        sys.stderr.flush()
        if self.sidecar_process:
            self.sidecar_process.terminate()
            try:
                self.sidecar_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.sidecar_process.kill()
        event.accept()

def main():
    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    
    dev_mode = os.environ.get("ZMAN_DEV") == "1"
    window = MainWindow(dev_mode=dev_mode)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
