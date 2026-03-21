from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Generator, List, Any, Dict, Optional

from core import os_utils, config_writer
from core.device_management import configurator
from core.config import CONFIG_PATH

@dataclass
class StepUpdate:
    """
    Emitted by the generator to update the UI.
    start_step: (title) -> Starts a new step row.
    log_line: (text) -> Appends to current step's terminal.
    step_done: (success, message) -> Marks current step as finished.
    """
    type: str # 'start_step', 'log_line', 'step_done'
    payload: Any

def apply_live_changes_generator(changes: List[Any], device_configs_snapshot: Dict[str, Any]) -> Generator[StepUpdate, None, None]:
    """
    Generator that yields StepUpdate events for a list of changes.
    Matches the logic of ConfigureLogic.apply_worker_batch but streams progress.
    """
    
    # 1. Privileges Handling (Mock or Real)
    # Ideally we'd do a "sudo -v" or "pkexec echo" check here, but we'll assume pkexec works
    
    for action, dev, desc in changes:
        try:
            if action == "DELETE":
                yield from _remove_device_generator(dev)
            
            elif action in ("CREATE", "MODIFY"):
                cfg = device_configs_snapshot.get(dev)
                if not cfg:
                     yield StepUpdate("start_step", f"Processing {dev}")
                     yield StepUpdate("log_line", f"Error: Missing config for {dev}")
                     yield StepUpdate("step_done", (False, "Missing config"))
                     continue
                     
                yield from _apply_device_generator(dev, cfg)
                
        except Exception as e:
            # Catch-all for unexpected crashes in generator
            yield StepUpdate("log_line", f"CRITICAL ERROR: {str(e)}")
            yield StepUpdate("step_done", (False, str(e)))
            return

def _remove_device_generator(device_name: str) -> Generator[StepUpdate, None, None]:
    step_title = f"Removing {device_name}"
    yield StepUpdate("start_step", step_title)
    
    try:
        # Get helper path
        helper = os_utils._get_helper_path()
        
        # Build batched command: pkexec zman-helper.py live-remove <device> <config_path>
        cmd = ["pkexec", helper, "live-remove", device_name, CONFIG_PATH]
        
        yield StepUpdate("log_line", f"Runing batched removal for {device_name}...")
        
        # We need to provide the 'new' content for the config file.
        # remove_device_from_config returns the rendered content of the file *minus* the device.
        ok, err, rendered = config_writer.remove_device_from_config(device_name)
        if not ok:
            yield StepUpdate("log_line", f"Config Update Failed: {err}")
            yield StepUpdate("step_done", (False, err))
            return

        # Stream the output. Steps are marked with ">> "
        yield from _stream_subprocess(cmd, input_text=rendered)
        yield StepUpdate("step_done", (True, "Removed"))
        
    except Exception as e:
        yield StepUpdate("log_line", f"Exception: {str(e)}")
        yield StepUpdate("step_done", (False, str(e)))


def _apply_device_generator(device_name: str, ui_cfg: Dict[str, Any]) -> Generator[StepUpdate, None, None]:
    step_title = f"Configuring {device_name}"
    yield StepUpdate("start_step", step_title)
    
    # --- Capture State for Rollback ---
    original_config_content = ""
    try:
        # We read as text. If file doesn't exist, we assume empty string (safe for new installs).
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                original_config_content = f.read()
    except Exception as e:
        yield StepUpdate("log_line", f"Warning: Failed to backup config: {e}")
        # We proceed, but rollback might be empty.
    
    try:
        # 1. Convert UI Config to Updates
        from ui.configure_logic import ConfigureLogic
        updates = ConfigureLogic._build_update_dict(ui_cfg)
        
        yield StepUpdate("log_line", "Generating configuration...")
        ok, err, rendered = config_writer.update_zram_config(device_name, updates)
        if not ok:
            yield StepUpdate("log_line", f"Error: {err}")
            yield StepUpdate("step_done", (False, err))
            return
            
        # 2. Run Batched Command
        helper = os_utils._get_helper_path()
        cmd = ["pkexec", helper, "live-apply", device_name, CONFIG_PATH]
        
        yield from _stream_subprocess(cmd, input_text=rendered)
        yield StepUpdate("step_done", (True, "Applied"))

    except Exception as e:
        # --- FAILURE DETECTED ---
        yield StepUpdate("log_line", f"Operation failed: {str(e)}")
        yield StepUpdate("step_done", (False, "Failed"))
        
        # --- ROLLBACK SEQUENCE ---
        yield StepUpdate("start_step", f"Rolling back {device_name}")
        yield StepUpdate("log_line", "Attempting to restore previous configuration...")
        
        try:
            helper = os_utils._get_helper_path()
            # Reuse live-apply to restore the original content
            cmd_rollback = ["pkexec", helper, "live-apply", device_name, CONFIG_PATH]
            yield from _stream_subprocess(cmd_rollback, input_text=original_config_content)
            
            yield StepUpdate("log_line", "Rollback successful. System restored.")
            yield StepUpdate("step_done", (True, "Restored"))
            
        except Exception as rb_e:
            yield StepUpdate("log_line", f"CRITICAL: Rollback failed: {rb_e}")
            yield StepUpdate("log_line", "Manual intervention required.")
            yield StepUpdate("step_done", (False, "Rollback Failed"))

def _stream_subprocess(cmd: List[str], check: bool = True, input_text: Optional[str] = None) -> Generator[StepUpdate, None, None]:
    """Helper to bridge os_utils.stream_command to StepUpdate events."""
    try:
        # Parse the output stream
        for line in os_utils.stream_command(cmd, input_text=input_text):
            if line.startswith(">> "):
                # Start new step
                step_name = line[3:].strip() # Remove ">> "

            
                yield StepUpdate("step_done", (True, "Done")) # Close previous
                yield StepUpdate("start_step", step_name) # Start new
                
            else:
                yield StepUpdate("log_line", line)
                
    except os_utils.SystemCommandError as e:
        yield StepUpdate("log_line", f"Command failed: code {e.returncode}")
        if check:
            raise e
