use std::process::{Command, Stdio, Child};
use std::sync::Mutex;
use std::io::{BufReader, BufRead, Write};
use tauri::{Manager, Emitter};
use serde_json::Value;

struct SidecarState {
    stdin: Mutex<Option<std::process::ChildStdin>>,
    child: Mutex<Option<Child>>,
}

fn find_sidecar_path() -> Option<std::path::PathBuf> {
    let possible_paths = vec![
        // 1. Relative to current working directory (dev mode)
        std::env::current_dir().ok().map(|p| p.join("sidecar.py")),
        std::env::current_dir().ok().map(|p| p.join("../sidecar.py")),
        std::env::current_dir().ok().map(|p| p.join("webUI/sidecar.py")),
        // 2. Relative to current executable (production mode)
        std::env::current_exe().ok().and_then(|p| p.parent().map(|parent| parent.join("sidecar.py"))),
        std::env::current_exe().ok().and_then(|p| p.parent().map(|parent| parent.join("../sidecar.py"))),
        std::env::current_exe().ok().and_then(|p| p.parent().map(|parent| parent.join("../../sidecar.py"))),
    ];

    for path_opt in possible_paths {
        if let Some(path) = path_opt {
            if path.exists() {
                return Some(path);
            }
        }
    }
    None
}

#[tauri::command]
fn send_to_sidecar(state: tauri::State<'_, SidecarState>, action: String, payload: Option<Value>) -> Result<(), String> {
    let mut stdin_lock = state.stdin.lock().unwrap();
    if let Some(ref mut stdin) = *stdin_lock {
        let mut msg = match payload {
            Some(Value::Object(obj)) => Value::Object(obj),
            _ => serde_json::Map::new().into(),
        };
        if let Some(obj) = msg.as_object_mut() {
            obj.insert("action".to_string(), Value::String(action));
        }
        let mut msg_str = serde_json::to_string(&msg).map_err(|e| e.to_string())?;
        msg_str.push('\n');
        stdin.write_all(msg_str.as_bytes()).map_err(|e| e.to_string())?;
        stdin.flush().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Sidecar stdin is not available".to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[cfg(target_os = "linux")]
    {
        std::env::set_var("GDK_DEBUG", "gl-no-fractional");
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    }

    tauri::Builder::default()
        .manage(SidecarState {
            stdin: Mutex::new(None),
            child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![send_to_sidecar])
        .setup(|app| {
            // Find the sidecar path
            if let Some(sidecar_path) = find_sidecar_path() {
                println!("[Rust] Found sidecar at: {:?}", sidecar_path);
                
                // Spawn the Python sidecar in Stdio IPC mode (no --port argument)
                let child_res = Command::new("python3")
                    .arg(sidecar_path)
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped())
                    .spawn();
                
                match child_res {
                    Ok(mut c) => {
                        println!("[Rust] Spawned python3 sidecar process in Stdio IPC mode");
                        
                        let stdin = c.stdin.take().unwrap();
                        let stdout = c.stdout.take().unwrap();
                        let stderr = c.stderr.take().unwrap();
                        
                        // Store stdin and child in state
                        let state = app.state::<SidecarState>();
                        *state.stdin.lock().unwrap() = Some(stdin);
                        *state.child.lock().unwrap() = Some(c);
                        
                        // Spawn thread to read stdout and emit events to frontend
                        let app_handle_clone = app.handle().clone();
                        std::thread::spawn(move || {
                            let reader = BufReader::new(stdout);
                            for line in reader.lines() {
                                match line {
                                    Ok(l) => {
                                        if let Ok(json_val) = serde_json::from_str::<Value>(&l) {
                                            if let Err(e) = app_handle_clone.emit("sidecar-message", json_val) {
                                                eprintln!("[Rust] Failed to emit sidecar message: {}", e);
                                            }
                                        } else {
                                            eprintln!("[Rust] Failed to parse sidecar stdout line as JSON: {}", l);
                                        }
                                    }
                                    Err(e) => {
                                        eprintln!("[Rust] Error reading sidecar stdout: {}", e);
                                        break;
                                    }
                                }
                            }
                            println!("[Rust] Sidecar stdout reader thread exiting");
                        });
                        
                        // Spawn thread to read stderr and print to console
                        std::thread::spawn(move || {
                            let reader = BufReader::new(stderr);
                            for line in reader.lines() {
                                match line {
                                    Ok(l) => {
                                        eprintln!("[Sidecar Stderr] {}", l);
                                    }
                                    Err(e) => {
                                        eprintln!("[Rust] Error reading sidecar stderr: {}", e);
                                        break;
                                    }
                                }
                            }
                            println!("[Rust] Sidecar stderr reader thread exiting");
                        });
                    }
                    Err(e) => {
                        eprintln!("[Rust] Failed to spawn python3 sidecar: {}", e);
                    }
                }
            } else {
                eprintln!("[Rust] Could not find sidecar.py in any expected location!");
            }

            #[cfg(target_os = "linux")]
            {
                use gtk::prelude::*;
                use webkit2gtk::WebView;
                
                if let Some(window) = app.get_webview_window("main") {
                    if let Ok(gtk_window) = window.gtk_window() {
                        // Traverse GTK Container structures: Window -> Box -> WebKitWebView
                        let webview_widget = gtk_window
                            .children()
                            .into_iter()
                            .next()
                            .and_then(|child| child.downcast::<gtk::Box>().ok())
                            .and_then(|box_layout| {
                                box_layout
                                    .children()
                                    .into_iter()
                                    .filter_map(|widget| widget.downcast::<WebView>().ok())
                                    .next()
                                });

                         if let Some(web_view) = webview_widget {
                             // Enable smooth scrolling for a native desktop feel
                             use webkit2gtk::{WebViewExt, SettingsExt};
                             if let Some(settings) = WebViewExt::settings(&web_view) {
                                 SettingsExt::set_enable_smooth_scrolling(&settings, true);
                                 println!("[Rust] Enabled WebKitGTK smooth scrolling");
                             }

                             unsafe {
                                 let raw_view: *mut gobject_sys::GObject = web_view.as_ptr() as *mut _;
                                 let gesture_key = "wk-view-zoom-gesture\0".as_ptr() as *const std::os::raw::c_char;
                                 let gesture_ptr = gobject_sys::g_object_get_data(raw_view, gesture_key);

                                 if !gesture_ptr.is_null() {
                                     gobject_sys::g_signal_handlers_destroy(gesture_ptr as *mut gobject_sys::GObject);
                                     println!("[Rust] Neutralized WebKitGTK zoom gesture");
                                 }
                             }
                         }
                    }
                }
            }
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill the sidecar process when the window is destroyed
                let app = window.app_handle();
                let child = {
                    let state = app.state::<SidecarState>();
                    let x = state.child.lock().unwrap().take();
                    x
                };
                if let Some(mut c) = child {
                    match c.kill() {
                        Ok(_) => println!("[Rust] Killed sidecar process"),
                        Err(e) => eprintln!("[Rust] Failed to kill sidecar process: {}", e),
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
