
import threading
from typing import Dict, List, Any, Set, Tuple
from gi.repository import GLib

import io
import difflib
from core import config as zram_config
from core import zdevice_ctl, config_writer
from core.zdevice_ctl import UnitResult

class ConfigureLogic:
    """
    Helper class to handle business logic for ConfigurePage.
    Separates data processing and system interactions from GTK UI code.
    """
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Returns the default configuration dictionary for a new device."""
        return {
            "size_mode": 0, # 0=Default(50%), 1=RAM(100%), 2=Custom
            "custom_size": "",
            "algorithm": 0, # 0=zstd, 1=lzo-rle, 2=lz4, 3=Custom
            "custom_algorithm": "",
            "priority": 100,
            "host_limit_enabled": False,
            "host_limit_mb": 2048,
            "resident_limit": "",
            "writeback_dev": "None Selected",
            "options": "",
            "fs_mode": False,
            "fs_type": 1, # 1=ext4
            "mount_point": ""
        }

    @staticmethod
    def calculate_changes(form_state: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
        """
        Compares the provided UI form state against the actual on-disk configuration.
        Returns a list of changes: [(Action, Device, Details), ...]
        
        Action: "CREATE", "DELETE", "MODIFY"
        """
        changes = []
        
        # 1. Read DISK Config (Source of Truth)
        disk_parser = zram_config.read_zram_config()
        # Filter out global section 'zram-generator'
        disk_devices = {k for k in disk_parser.keys() if k != 'zram-generator'}
        
        # 2. Read UI Config (Proposed)
        # Filter out None keys if any slipped in
        ui_devices = {k for k in form_state.keys() if k is not None}
        
        # A. Deletions (In DISK but not in UI)
        for dev in disk_devices - ui_devices:
            changes.append(("DELETE", dev, ["Remove from config"]))
            
        # B. Creations (In UI but not in DISK)
        for dev in ui_devices - disk_devices:
            changes.append(("CREATE", dev, ["Add to config"]))
            
        # C. Modifications (In Both)
        for dev in ui_devices.intersection(disk_devices):
            ui_cfg = form_state[dev]
            disk_sect = disk_parser[dev] if dev in disk_parser else {}
            
            diffs = ConfigureLogic._compare_device_config(ui_cfg, disk_sect)
            
            # Add to mods if any diffs found
            if diffs:
                changes.append(("MODIFY", dev, diffs))
                
        return changes

    @staticmethod
    def _compare_device_config(ui_cfg: Dict[str, Any], disk_sect: Dict[str, str]) -> List[str]:
        """Internal helper to compare a single device's UI config vs Disk config."""
        diffs = []
        
        # 1. Size
        ui_size_str = ""
        if ui_cfg["size_mode"] == 1: 
            ui_size_str = "ram"
        elif ui_cfg["size_mode"] == 0: 
            ui_size_str = "min(ram / 2, 4096)"
        else: 
            ui_size_str = ui_cfg["custom_size"] or ""
        
        disk_size = disk_sect.get("zram-size", "")
        if ui_size_str != disk_size:
            diffs.append(f"Size: {disk_size or 'None'} → {ui_size_str or 'None'}")

        # 2. Algorithm
        ui_algos = ["zstd", "lzo-rle", "lz4"]
        if ui_cfg["algorithm"] == 3:
            ui_algo_str = ui_cfg["custom_algorithm"] or ""
        else:
            ui_algo_str = ui_algos[ui_cfg["algorithm"]]
                
        disk_algo = disk_sect.get("compression-algorithm", "")
        if ui_algo_str != disk_algo:
            diffs.append(f"Algo: {disk_algo or 'None'} → {ui_algo_str}")

        # 3. Priority
        ui_prio = str(ui_cfg["priority"])
        disk_prio = disk_sect.get("swap-priority", "100")
        if ui_prio != disk_prio:
            diffs.append(f"Priority: {disk_prio} → {ui_prio}")

        # 4. Resident Limit
        ui_res = ui_cfg["resident_limit"]
        disk_res = disk_sect.get("zram-resident-limit", "")
        if ui_res != disk_res:
            diffs.append(f"Res. Limit: {disk_res or 'None'} → {ui_res or 'None'}")
            
        # 5. Options
        ui_opt = ui_cfg["options"]
        disk_opt = disk_sect.get("options", "")
        if ui_opt != disk_opt:
            diffs.append(f"Options: {disk_opt or 'None'} → {ui_opt or 'None'}")

        # 6. Writeback Device
        ui_wb = ui_cfg["writeback_dev"]
        if ui_wb == "None Selected": 
            ui_wb = ""
        disk_wb = disk_sect.get("writeback-device", "")
        if ui_wb != disk_wb:
            diffs.append(f"Writeback: {disk_wb or 'None'} → {ui_wb or 'None'}")
            
        return diffs

    @staticmethod
    def generate_preview_config(device_configs: Dict[str, Any]) -> str:
        """
        Generates the full text of the zram-generator.conf file as it WOULD look 
        if the current UI state were applied.
        """
        # 1. Start with current config (to preserve comments/globals)
        cfg = zram_config.read_zram_config()
        
        # 2. Apply all UI states
        # Identify devices to process
        # A. Remove devices present in Disk but not in UI
        disk_devices = {k for k in cfg.keys() if k != 'zram-generator'}
        ui_devices = {k for k in device_configs.keys()}
        
        for dev in disk_devices - ui_devices:
            del cfg[dev]
            
        # B. Update/Add devices from UI
        for dev in ui_devices:
            if dev not in cfg:
                cfg[dev] = {}
            
            updates = ConfigureLogic._build_update_dict(device_configs[dev])
            for key, value in updates.items():
                if value is None:
                    if key in cfg[dev]:
                        del cfg[dev][key]
                else:
                    cfg[dev][key] = str(value)
                    
        # 3. Render to string
        try:
            s = io.BytesIO()
            cfg.write(s)
            return s.getvalue().decode('utf-8').strip()
        except Exception:
            return ""

    @staticmethod
    def get_config_diff(device_configs: Dict[str, Any]) -> str:
        """
        Returns a unified diff string between the current disk config and the UI state.
        """
        # 1. Get Current Disk Content
        try:
            with open(zram_config.get_active_config_path(), 'r') as f:
                current_lines = f.readlines()
        except (FileNotFoundError, TypeError):
            current_lines = []
            
        # 2. Get Preview Content
        new_content = ConfigureLogic.generate_preview_config(device_configs)
        new_lines = [line + "\n" for line in new_content.splitlines()]
        
        # 3. Generate Diff
        diff = difflib.unified_diff(
            current_lines, 
            new_lines, 
            fromfile='Current Config', 
            tofile='New Config'
        )
        
        return "".join(diff)

    @staticmethod
    def apply_worker_batch(changes: List[Any], device_configs_snapshot: Dict[str, Any], live_apply: bool) -> Tuple[bool, List[str]]:
        """
        Executes the list of changes.
        Returns (overall_success, logs_list).
        """
        logs = []
        overall_success = True
        
        try:
            for action, dev, desc in changes:
                res = None
                if action == "DELETE":
                    # Pass apply_now=live_apply
                    res = zdevice_ctl.remove_device_config(dev, apply_now=live_apply)
                    
                else: # CREATE or MODIFY
                    # Construct updates dict from snapshot
                    cfg = device_configs_snapshot.get(dev)
                    if not cfg:
                        logs.append(f"Error: Missing config for {dev}")
                        overall_success = False
                        continue
                        
                    updates = ConfigureLogic._build_update_dict(cfg)
                    
                    # Pass reload_daemon=live_apply
                    # If live_apply is True, we reload daemon and restart service
                    res = zdevice_ctl.apply_device_config(
                        dev, 
                        updates, 
                        restart_service=live_apply, 
                        reload_daemon=live_apply
                    )
                
                logs.append(f"{dev}: {res.message}")
                if not res.success:
                    overall_success = False
            
        except Exception as e:
            overall_success = False
            logs.append(str(e))
            
        return overall_success, logs

    @staticmethod
    def _build_update_dict(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to convert UI config dict to Systemd config updates."""
        updates = {}
        if cfg["size_mode"] == 1: updates["zram-size"] = "ram"
        elif cfg["size_mode"] == 0: updates["zram-size"] = "min(ram / 2, 4096)"
        else: updates["zram-size"] = cfg["custom_size"]
        
        algos = ["zstd", "lzo-rle", "lz4"]
        if cfg["algorithm"] == 3:
            updates["compression-algorithm"] = cfg["custom_algorithm"]
        else:
            updates["compression-algorithm"] = algos[cfg["algorithm"]]
            
        updates["swap-priority"] = str(cfg["priority"])
        
        # New Fields Updates
        updates["zram-resident-limit"] = cfg["resident_limit"] if cfg["resident_limit"] else None
        updates["options"] = cfg["options"] if cfg["options"] else None

        wb = cfg["writeback_dev"]
        updates["writeback-device"] = wb if wb != "None Selected" else None
        
        # FS Mode omitted for brevity/safety unless enabled
        updates["fs-type"] = None
        updates["mount-point"] = None
        
        return updates