import sys
import os
import json
import time
import argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

# Add project root to sys.path to enable imports of core and modules
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import core modules
import psutil
from core.device_management import prober
from core.utils.units import parse_size_to_bytes
from core import health
from modules import psi
from modules import runtime
from core import boot_config
from core.device_management import configurator as zram_configurator
from core.hibernation import configurator as hibernate_configurator
from core.hibernation.prober import check_hibernation_readiness
from core.utils.privilege import pkexec_update_boot

# Global list of active SSE client queues
sse_queues = []
sse_queues_lock = threading.Lock()

class SidecarHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Redirect HTTP logs to stderr to keep stdout clean
        sys.stderr.write(f"[Sidecar HTTP] {format % args}\n")
        sys.stderr.flush()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            sys.stderr.write("[Sidecar] New SSE client connected\n")
            sys.stderr.flush()
            
            import queue
            q = queue.Queue()
            with sse_queues_lock:
                sse_queues.append(q)
            
            try:
                while True:
                    try:
                        msg = q.get(timeout=5)
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                with sse_queues_lock:
                    if q in sse_queues:
                        sse_queues.remove(q)
                sys.stderr.write("[Sidecar] SSE client disconnected\n")
                sys.stderr.flush()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith('/api/'):
            action = self.path[5:]
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {}
                
            response_data = handle_action(action, payload)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

stdout_lock = threading.Lock()

def write_to_stdout(data):
    with stdout_lock:
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()

def handle_action(action, payload):
    # Log to stderr to keep stdout clean for JSON messages
    sys.stderr.write(f"[Sidecar] Action received: {action} with payload: {payload}\n")
    sys.stderr.flush()
    try:
        if action == "ping":
            return {"status": "ok", "pong": True}
        
        elif action == "get_dashboard_data":
            # Return immediate telemetry snapshot
            return get_telemetry_data()
        
        elif action == "apply_tuning":
            swappiness = payload.get("swappiness")
            vfs_cache_pressure = payload.get("vfs_cache_pressure")
            cpu_governor = payload.get("cpu_governor")
            
            success = True
            errors = []
            
            # 1. Apply sysctl values
            sysctl_settings = {}
            if swappiness is not None:
                sysctl_settings["vm.swappiness"] = str(swappiness)
            if vfs_cache_pressure is not None:
                sysctl_settings["vm.vfs_cache_pressure"] = str(vfs_cache_pressure)
                
            if sysctl_settings:
                res = boot_config.apply_sysctl_values(sysctl_settings)
                if not res.success:
                    success = False
                    errors.append(res.message)
                    
            # 2. Apply CPU governor
            if cpu_governor:
                gov_success = runtime.set_cpu_governor(cpu_governor)
                if not gov_success:
                    success = False
                    errors.append(f"Failed to set CPU governor to {cpu_governor}")
                    
            if success:
                return {"status": "success", "message": "Tuning settings applied successfully."}
            else:
                return {"status": "error", "message": "; ".join(errors)}
        
        elif action == "configure_zram":
            device = payload.get("device", "zram0")
            algo = payload.get("algo", "zstd")
            size = payload.get("size", "1G")
            backingDev = payload.get("backingDev")
            
            # Convert empty string or 'none' backingDev to None
            if backingDev in ("", "none", "None Selected", "none selected"):
                backingDev = None
            
            updates = {
                "compression-algorithm": algo,
                "zram-size": size
            }
            if backingDev is not None:
                updates["writeback-device"] = backingDev
            else:
                updates["writeback-device"] = None
            
            res = zram_configurator.apply_device_config(device, updates, restart_service=True)
            if res.success:
                return {"status": "success", "message": f"Device {device} configured and restarted."}
            else:
                return {"status": "error", "message": res.message}
        
        elif action == "reset_zram":
            device = payload.get("device", "zram0")
            res = zram_configurator.restart_unit_for_device(device)
            if res.success:
                return {"status": "success", "message": f"Device {device} reset successfully."}
            else:
                return {"status": "error", "message": res.message}
        
        elif action == "remove_zram":
            device = payload.get("device", "zram0")
            res = zram_configurator.remove_device_config(device, apply_now=True)
            if res.success:
                return {"status": "success", "message": f"Device {device} config removed."}
            else:
                return {"status": "error", "message": res.message}
        
        elif action == "setup_hibernation":
            swap_path = payload.get("swap_path", "/swapfile")
            size_mb = int(payload.get("size_mb", 16384))
            priority = int(payload.get("priority", 0))
            
            res = hibernate_configurator.apply_full_setup(swap_path, size_mb, priority)
            if res.success:
                return {"status": "success", "message": "Hibernation setup completed successfully."}
            else:
                return {"status": "error", "message": res.message}
        
        elif action == "update_boot":
            success, msg = pkexec_update_boot()
            if success:
                return {"status": "success", "message": "Boot parameters updated successfully."}
            else:
                return {"status": "error", "message": msg}
        
        return {"status": "error", "message": f"Unknown action: {action}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_telemetry_data():
    # RAM
    try:
        vm = psutil.virtual_memory()
        ram_data = {"total": vm.total, "used": vm.used}
    except Exception:
        ram_data = {"total": 1, "used": 0}

    # ZRAM Devices
    devices_data = []
    try:
        devices = prober.list_devices()
        for dev in devices:
            try:
                disk_bytes = parse_size_to_bytes(dev.disksize or '0')
                data_bytes = parse_size_to_bytes(dev.data_size or '0')
                compr_bytes = parse_size_to_bytes(dev.compr_size or '0')
                mem_used_total_bytes = parse_size_to_bytes(dev.total_size or '0')
            except Exception:
                disk_bytes, data_bytes, compr_bytes, mem_used_total_bytes = 0, 0, 0, 0

            is_swap = False
            if dev.mountpoint and "SWAP" in dev.mountpoint:
                is_swap = True
            elif dev.name and dev.name.startswith("zram"):
                is_swap = True
            
            wb_stats = prober.get_writeback_status(dev.name)
            
            devices_data.append({
                "name": dev.name,
                "algo": dev.algorithm or "zstd",
                "usedBytes": data_bytes,
                "totalBytes": disk_bytes,
                "origBytes": data_bytes,
                "comprBytes": compr_bytes,
                "memUsedTotalBytes": mem_used_total_bytes,
                "ramTotal": ram_data["total"],
                "isSwap": is_swap,
                "backingDev": wb_stats.backing_dev if wb_stats else None,
                "wbNum": int(wb_stats.num_writeback or 0) if wb_stats else 0,
                "wbFailed": int(wb_stats.writeback_failed or 0) if wb_stats else 0
            })
    except Exception as e:
        print(f"[Sidecar Telemetry] Error listing devices: {e}")

    # Swaps
    swaps_data = []
    try:
        swaps = health.get_all_swaps()
        for swap in swaps:
            def kb_to_human(kb):
                if kb < 1024:
                    return f"{kb} KiB"
                mb = kb / 1024
                if mb < 1024:
                    return f"{mb:.1f} MiB"
                gb = mb / 1024
                return f"{gb:.2f} GiB"
            
            swaps_data.append({
                "name": swap.name,
                "size": kb_to_human(swap.size_kb),
                "used": kb_to_human(swap.used_kb),
                "size_bytes": swap.size_kb * 1024,
                "used_bytes": swap.used_kb * 1024,
                "priority": swap.priority
            })
    except Exception as e:
        sys.stderr.write(f"[Sidecar Telemetry] Error getting swaps: {e}\n")
        sys.stderr.flush()

    # PSI
    psi_data = {}
    try:
        for res in ["cpu", "memory", "io"]:
            stats = psi.get_psi(res)
            if stats:
                psi_data[res] = {
                    "some": stats.some_avg10,
                    "full": stats.full_avg10
                }
            else:
                psi_data[res] = {"some": 0.0, "full": 0.0}
    except Exception as e:
        sys.stderr.write(f"[Sidecar Telemetry] Error getting PSI: {e}\n")
        sys.stderr.flush()

    # Hibernation Readiness
    hibernation_data = {
        "ready": False,
        "secure_boot": "disabled",
        "swap_total": 0,
        "ram_total": ram_data["total"],
        "recommended_swap_bytes": ram_data["total"] * 2,
        "message": "Hibernation status unknown"
    }
    try:
        hr = check_hibernation_readiness()
        hibernation_data = {
            "ready": hr.ready,
            "secure_boot": hr.secure_boot,
            "swap_total": hr.swap_total,
            "ram_total": hr.ram_total,
            "recommended_swap_bytes": hr.recommended_swap_bytes,
            "message": hr.message
        }
    except Exception as e:
        sys.stderr.write(f"[Sidecar Telemetry] Error getting hibernation readiness: {e}\n")
        sys.stderr.flush()

    # System Health
    health_data = {
        "zramctl_available": True,
        "systemd_available": True,
        "sysfs_root_accessible": True,
        "zswap": {"available": False, "enabled": False, "detail": ""},
        "journal_available": True,
        "kernel_version": "",
        "devices_summary": "",
        "notes": []
    }
    try:
        hr = health.check_system_health()
        health_data = {
            "zramctl_available": hr.zramctl_available,
            "systemd_available": hr.systemd_available,
            "sysfs_root_accessible": hr.sysfs_root_accessible,
            "zswap": {
                "available": hr.zswap.available,
                "enabled": hr.zswap.enabled,
                "detail": hr.zswap.detail
            },
            "journal_available": hr.journal_available,
            "kernel_version": hr.kernel_version,
            "devices_summary": hr.devices_summary,
            "notes": hr.notes
        }
    except Exception as e:
        sys.stderr.write(f"[Sidecar Telemetry] Error getting system health: {e}\n")
        sys.stderr.flush()

    # Tuning settings
    tuning_data = {
        "swappiness": 60,
        "vfs_cache_pressure": 100,
        "cpu_governor": "powersave",
        "available_governors": ["powersave", "performance", "schedutil"]
    }
    try:
        sw = boot_config.get_swappiness()
        if sw is not None:
            tuning_data["swappiness"] = sw
        tuning_data["vfs_cache_pressure"] = runtime.get_vfs_cache_pressure()
        tuning_data["cpu_governor"] = runtime.get_current_cpu_governor()
        tuning_data["available_governors"] = runtime.get_available_cpu_governors()
    except Exception as e:
        sys.stderr.write(f"[Sidecar Telemetry] Error getting tuning settings: {e}\n")
        sys.stderr.flush()

    return {
        "action": "dashboard_update",
        "ram": ram_data,
        "devices": devices_data,
        "swaps": swaps_data,
        "psi": psi_data,
        "hibernation": hibernation_data,
        "tuning": tuning_data,
        "health": health_data
    }

def telemetry_broadcaster(use_http=False):
    while True:
        try:
            data = get_telemetry_data()
            if use_http:
                # Push to SSE queues
                with sse_queues_lock:
                    if len(sse_queues) > 0:
                        message = f"data: {json.dumps(data)}\n\n".encode('utf-8')
                        for q in sse_queues:
                            q.put(message)
            else:
                # Write to stdout
                write_to_stdout(data)
        except Exception as e:
            sys.stderr.write(f"[Sidecar Telemetry Error] {e}\n")
            sys.stderr.flush()
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Port to run HTTP/SSE server on")
    args = parser.parse_args()

    if args.port:
        sys.stderr.write(f"[Sidecar] Starting HTTP/SSE server on port {args.port}\n")
        sys.stderr.flush()
        
        # Start telemetry broadcaster thread in HTTP mode
        broadcaster_thread = threading.Thread(target=telemetry_broadcaster, args=(True,), daemon=True)
        broadcaster_thread.start()
        
        server = ThreadingHTTPServer(('127.0.0.1', args.port), SidecarHTTPHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    else:
        sys.stderr.write("[Sidecar] Starting Stdio IPC loop\n")
        sys.stderr.flush()
        
        # Start telemetry broadcaster thread in Stdio mode
        broadcaster_thread = threading.Thread(target=telemetry_broadcaster, args=(False,), daemon=True)
        broadcaster_thread.start()

        # Read actions from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            action = payload.get("action")
            if not action:
                continue
                
            try:
                response = handle_action(action, payload)
                if response is not None:
                    if isinstance(response, dict):
                        if "action" not in response:
                            response["action"] = action
                        if "requestId" in payload:
                            response["requestId"] = payload["requestId"]
                        write_to_stdout(response)
            except Exception as e:
                write_to_stdout({"action": action, "status": "error", "message": str(e)})

if __name__ == "__main__":
    main()
