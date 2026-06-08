#!/usr/bin/env gjs

/**
 * @fileoverview Z-Manager UI Shell using Gjs (GNOME JavaScript).
 * Translates webUI/server.py functionality to GTK4 and WebKitGTK 6.0.
 */

// Global fixes for WebKitGTK blur and fractional scaling issues on Linux:
// 1. Disable fractional scaling interpolation in GL renderer to keep rendering grid-aligned
imports.gi.GLib.setenv("GDK_DEBUG", "gl-no-fractional", true);
// 2. Disable DMA-BUF renderer to bypass driver-specific compositing conflicts on Intel/NVIDIA
imports.gi.GLib.setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "1", true);

imports.gi.versions.Gtk = '3.0';
imports.gi.versions.WebKit2 = '4.1';

const Gtk = imports.gi.Gtk;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const WebKit = imports.gi.WebKit2;
const GObject = imports.gi.GObject;
const System = imports.system;

/**
 * @class ZManagerWindow
 * @extends Gtk.ApplicationWindow
 * @description The main window of the Z-Manager application, hosting the WebKit WebView.
 */
const ZManagerWindow = GObject.registerClass({
    GTypeName: 'ZManagerWindow',
}, class ZManagerWindow extends Gtk.ApplicationWindow {
    /**
     * @param {Gtk.Application} app The parent application instance.
     * @param {Gio.Subprocess} sidecarProcess The spawned sidecar subprocess.
     */
    _init(app, sidecarProcess) {
        super._init({
            application: app,
            title: "Z-Manager",
            default_width: 1024,
            default_height: 768
        });

        this.sidecar_process = sidecarProcess;

        // Create WebKit WebView
        /** @type {WebKit.WebView} */
        this.webview = new WebKit.WebView();

        // Configure WebKit Settings
        let settings = this.webview.get_settings();
        settings.set_enable_javascript(true);
        settings.set_enable_developer_extras(true); // Allow Web Inspector (Right click -> Inspect)
        settings.set_enable_write_console_messages_to_stdout(true); // Print console logs to terminal
        settings.set_allow_file_access_from_file_urls(true);
        settings.set_allow_universal_access_from_file_urls(true);
        settings.set_enable_smooth_scrolling(false); // Force discrete integer steps to prevent GPU subpixel scroll offsets
        settings.set_zoom_text_only(false);
        this.webview.set_zoom_level(1.0);

        // Setup Script Message Handler (Not needed for HTTP mode, but kept for fallback)
        let manager = this.webview.get_user_content_manager();
        manager.connect("script-message-received::zmanager", (mgr, jsResult) => {
            log("[Shell] Received native message, but running in HTTP mode.");
        });
        manager.register_script_message_handler("zmanager", null);

        // Add WebView to Window
        this.add(this.webview);

        // Load the Svelte App
        this.load_frontend();

        // Ensure the sidecar is cleaned up when the window is destroyed
        this.connect('destroy', () => {
            this.cleanup_sidecar();
        });
    }

    /**
     * @description Resolves frontend build/dev paths and loads the URI.
     */
    load_frontend() {
        let programPath = Gio.File.new_for_path(System.programInvocationName).get_path();
        let currentDir = GLib.path_get_dirname(programPath);

        let distDir = GLib.build_filenamev([currentDir, "dist"]);
        let indexFile = Gio.File.new_for_path(GLib.build_filenamev([distDir, "index.html"]));

        let devMode = GLib.getenv("ZMAN_DEV") === "1";

        if (devMode) {
            log("[Shell] Loading frontend from dev server: http://localhost:5173");
            this.webview.load_uri("http://localhost:5173");
        } else if (indexFile.query_exists(null)) {
            let fileUri = indexFile.get_uri();
            log(`[Shell] Loading frontend from local build: ${fileUri}`);
            this.webview.load_uri(fileUri);
        } else {
            let html = "<h1>Error: Frontend not built</h1><p>Run <code>pnpm build</code> in the webUI directory.</p>";
            this.webview.load_html(html, "localhost");
        }
    }

    /**
     * @description Terminates the sidecar process with SIGTERM, falling back to SIGKILL.
     */
    cleanup_sidecar() {
        if (this.sidecar_process) {
            log("[Shell] Killing sidecar process");
            try {
                this.sidecar_process.send_signal(15); // SIGTERM
                
                let loop = new GLib.MainLoop(null, false);
                let cancellable = new Gio.Cancellable();
                
                let timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2000, () => {
                    log("[Shell] Sidecar did not exit in 2s, forcing exit");
                    cancellable.cancel();
                    this.sidecar_process.force_exit();
                    loop.quit();
                    return GLib.SOURCE_REMOVE;
                });
                
                this.sidecar_process.wait_async(cancellable, (p, res) => {
                    try {
                        p.wait_finish(res);
                    } catch (e) {
                        // Might be cancelled or already exited
                    }
                    GLib.source_remove(timeoutId);
                    loop.quit();
                });
                
                loop.run();
            } catch (e) {
                log(`[Shell] Error terminating sidecar: ${e}`);
            }
            this.sidecar_process = null;
        }
    }
});

/**
 * @class ZManagerApp
 * @extends Gtk.Application
 * @description The application class that manages the main window and sidecar process lifecycle.
 */
const ZManagerApp = GObject.registerClass({
    GTypeName: 'ZManagerApp',
}, class ZManagerApp extends Gtk.Application {
    _init() {
        super._init({
            application_id: "com.zmanager.app",
            flags: Gio.ApplicationFlags.FLAGS_NONE
        });
        this.sidecar_process = null;
    }

    vfunc_activate() {
        let programPath = Gio.File.new_for_path(System.programInvocationName).get_path();
        let currentDir = GLib.path_get_dirname(programPath);
        let sidecarPath = GLib.build_filenamev([currentDir, "sidecar.py"]);

        log(`[Shell] Starting sidecar process via HTTP/SSE on port 8000: ${sidecarPath}`);
        try {
            this.sidecar_process = Gio.Subprocess.new(
                ['python3', sidecarPath, '--port', '8000'],
                Gio.SubprocessFlags.NONE
            );
        } catch (e) {
            log(`[Shell] Failed to start sidecar: ${e}`);
        }

        let win = this.active_window;
        if (!win) {
            win = new ZManagerWindow(this, this.sidecar_process);
        }
        win.show_all();
        win.present();
    }

    vfunc_shutdown() {
        let win = this.active_window;
        if (win && typeof win.cleanup_sidecar === 'function') {
            win.cleanup_sidecar();
        } else if (this.sidecar_process) {
            // Fallback cleanup in case window was not constructed or already destroyed
            log("[Shell] Killing sidecar process on shutdown fallback");
            try {
                this.sidecar_process.send_signal(15);
                this.sidecar_process.force_exit();
            } catch (e) {
                // Ignore
            }
        }
        super.vfunc_shutdown();
    }
});

let app = new ZManagerApp();
let status = app.run([System.programInvocationName].concat(ARGV));
System.exit(status);
