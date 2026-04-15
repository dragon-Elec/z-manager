# ui AI Context

Identity: `z-manager/ui` -> GTK4/Adwaita user interface for Z-Manager, providing status monitoring, configuration editing, and hibernation management.

## Rules
- !Rule: [pkexec > sudo] - Reason: GUI applications must use pkexec for privilege escalation to ensure proper authentication agent integration.
- !Rule: [GTK Template > Manual XML] - Reason: Predefined .ui files are preferred for complex layouts to keep python controllers focused on logic.
- !Rule: [Adw.Window > Gtk.Window] - Reason: Project uses Libadwaita for modern GNOME aesthetics and adaptive components.

## Atomic Notes
- !Pattern: [Page-on-Stack] - Reason: `MainWindow` uses a `Gtk.Stack` to swap between functional views (`StatusPage`, `ConfigurePage`, `TunePage`, `HibernatePage`).
- !Pattern: [Live Mode] - Reason: Changes can be applied immediately via `LiveOrchestrator` using a temporary service restart, bypassing the need for a full reboot.
- !Decision: [Cairo Custom Widgets] - Reason: Circular gauges and memory tubes are custom-drawn in Cairo to provide a high-density, visually rich dashboard.

## Index
- `__init__.py`: Package initialization.
- `configure_logic.py`: Non-UI logic for `ConfigurePage`.
- `configure_page.py`: Adw preferences page for editing zram configurations.
- `confirmation_dialog.py`: Unified diff and change summary dialog.
- `custom_widgets.py`: Cairo-based UI components (CircularWidget, MemoryTube).
- `device_picker.py`: Block device selector dialog.
- `global_config_dialog.py`: Dialog for editing global zram-generator settings.
- `health_button.py`: Status indicator for system health.
- `health_dialog.py`: Detailed system health report.
- `hibernate_page.py`: Hibernation and swap management interface.
- `live_orchestrator.py`: Logic for streaming live configuration changes.
- `live_window.py`: Progress window for live operations.
- `log_viewer.py`: Journal log inspection tool.
- `main_window.py`: Application entry point and navigation shell.
- `status_page.py`: Real-time monitoring dashboard.
- `tune_page.py`: Kernel parameter tuning interface.

## Audits

### [FILE: main_window.py] [STUB]
Role: Navigation shell and application hub using Adw.HeaderBar and Gtk.Stack.

/DNA/: [connect:nav_buttons -> stack.set_visible_child_name(name)] + [call:load_css() -> Path.resolve().parent.parent / "css" / "style.css"]

- SrcDeps: .status_page, .configure_page, .tune_page, .hibernate_page
- SysDeps: gi.repository{Gtk, Adw, Gdk}, pathlib

API:
  - MainWindow(Gtk.ApplicationWindow):
    - on_nav_button_toggled(button) => switches visible stack child.
    - on_window_state_change() -> updates maximize/restore icons.
    - load_css() -> applies global application styles.

### [FILE: status_page.py] [STUB]
Role: Real-time monitoring dashboard for ZRAM devices and system swap.

/DNA/: [wait:1s -> call:refresh() -> {prober.list_devices(), health.get_all_swaps()} -> diff:widgets -> update/create/remove]

- SrcDeps: core.health, core.device_management.prober, .custom_widgets, .health_button, .health_dialog
- SysDeps: gi.repository{Gtk, Adw, GLib}, psutil

API:
  - StatusPage(Adw.Bin):
    - refresh() -> full UI update of ZRAM cards and swap rows.
    - _update_health_button() -> checks system health and updates status icon.
!Caveat: refresh loop is only active when widget is mapped (visible).

### [FILE: configure_page.py] [STUB]
Role: Adw.PreferencesPage for editing zram-generator configuration files.

/DNA/: [if(changed) -> call:calculate_changes() -> call:show_confirmation() -> call:apply_worker_batch() -> wait:finish -> call:refresh]

- SrcDeps: .custom_widgets, .device_picker, .global_config_dialog, .configure_logic, .confirmation_dialog, .live_window, core.config
- SysDeps: gi.repository{Gtk, Adw, GLib}, threading

API:
  - ConfigurePage(Gtk.Box):
    - _load_form_state(device_name) -> syncs UI fields from disk config.
    - _on_apply_clicked() -> triggers confirmation and deployment flow.
    - _start_apply_process(changes) -> forks to LiveModeWindow or background worker.

### [FILE: configure_logic.py] [STUB]
Role: Business logic glue for zram device CRUD and deployment.

/DNA/: [call:calculate_changes(ui_state) -> diff(ui_state, disk_config) => List[Action, Device, Diffs]]

- SrcDeps: core.{config, config_writer}, core.device_management.configurator
- SysDeps: gi.repository{GLib}, threading, difflib, io

API:
  - ConfigureLogic:
    - calculate_changes(form_state) => returns Change List (CREATE/DELETE/MODIFY).
    - generate_preview_config(device_configs) => returns full rendered INI string.
    - apply_worker_batch(changes, snapshot, live_apply) => executes disk writes and service restarts.

### [FILE: custom_widgets.py] [STUB]
Role: Custom Cairo components for visual telemetry and profile cards.

/DNA/: [call:draw_circle() -> cr.arc() -> cairo.LINE_CAP_ROUND -> render:ghost_snake + solid_snake]

- SysDeps: gi.repository{Gtk, Gdk}, math, cairo

API:
  - CircularWidget(Gtk.Box): High-density gauge for compression efficiency and RAM usage.
  - MemoryTube(Gtk.DrawingArea): Stacked bar showing [Apps | ZRAM | Free] distribution.
  - ScenarioCard(Gtk.ToggleButton): Styled profile selection card.

### [FILE: live_orchestrator.py] [STUB]
Role: Generator-based orchestrator for streaming privileged system changes.

/DNA/: [yield:StepUpdate -> call:config_writer.update() -> pkexec:zman-helper -> yield:stream_command(logs)]

- SrcDeps: core.{config_writer, config}, core.utils.{io, common}, .configure_logic
- SysDeps: typing, dataclasses, logging

API:
  - apply_live_changes_generator(changes, snapshot) => yields StepUpdate events for UI streaming.
  - _apply_device_generator(device_name, ui_cfg) -> handles backup, apply, and automated rollback.

### [FILE: live_window.py] [STUB]
Role: Progress monitoring window for live configuration apply operations.

/DNA/: [gen:apply_live_changes_generator() -> loop:GLib.idle_add(_handle_update) -> render:StepRow]

- SrcDeps: .live_orchestrator
- SysDeps: gi.repository{Gtk, Adw, GLib}, threading

API:
  - LiveModeWindow(Adw.Window):
    - _handle_update(update) -> pushes logs and status changes to UI.
    - on_all_done() -> unlocks UI and displays final success/error report.

### [FILE: device_picker.py] [STUB]
Role: Modal dialog for selecting and validating block devices for writeback/hibernation.

/DNA/: [call:list_block_devices() -> loop:render:Adw.ActionRow -> if(mounted/fs) -> add_css_class(error) + set_sensitive(false)]

- SrcDeps: core.utils.block
- SysDeps: gi.repository{Gtk, Adw}

API:
  - DevicePickerDialog(Adw.Window):
    - em:device-selected(path) -> returns absolute /dev/ path of chosen device.

### [FILE: global_config_dialog.py] [STUB]
Role: Editor for the [zram-generator] global configuration section.

/DNA/: [call:_on_apply_clicked() -> yield:updates -> em:applied]

- SysDeps: gi.repository{Gtk, Adw}

API:
  - GlobalConfigDialog(Adw.Window):
    - edit: default algorithm and system-wide default size.

### [FILE: health_button.py] [STUB]
Role: Compact status indicator with dynamic color coding.

/DNA/: [call:set_state(HealthState) -> add_css_class(health-state) -> set_tooltip_text(msg)]

- SysDeps: gi.repository{Gtk, Adw}, enum

API:
  - HealthStatusButton(Gtk.Button):
    - set_state(state, subtitle) -> updates button icon and tooltip.

### [FILE: health_dialog.py] [STUB]
Role: Detailed diagnostics viewer with "Fix It" quick actions.

/DNA/: [render:Adw.PreferencesGroup -> if(zswap_conflict) -> render:fix_button]

- SrcDeps: core.health, .health_button, .log_viewer
- SysDeps: gi.repository{Gtk, Adw}

API:
  - HealthReportDialog(Adw.Window):
    - Displays sysfs access, zswap conflicts, systemd status, and journal logs.

### [FILE: hibernate_page.py] [DONE]
Role: Hibernation orchestration interface for swap provision and boot config.

/DNA/: [call:check_hibernation_readiness() -> fetch:recommended_swap_bytes -> {apply_full_setup() OR update_boot_config()}] + [apply_hibernation_policy() via systemd-tmpfiles]

- SrcDeps: core.hibernation{., provisioner, configurator}, core.utils.block, .device_picker
- SysDeps: gi.repository{Gtk, Adw}, threading

API:
  - HibernatePage(Adw.PreferencesPage):
    - _refresh_state() -> updates readiness UI and resume swap status.
    - _on_device_selected() -> handles 'ZRAM-Hibernation Paradox' via dynamic size suggestion.
    - _setup_worker(path) -> orchestrates full setup (swap + boot + policy).
    - _boot_worker(path) -> executes privileged GRUB, initramfs, and image_size updates.

### [FILE: confirmation_dialog.py] [STUB]
Role: High-density change confirmation with unified diff viewer.

/DNA/: [call:difflib.unified_diff(old, new) -> render:Gtk.TextView + tags:{add, remove, header}]

- SysDeps: gi.repository{Gtk, Adw, Gdk}, difflib

API:
  - ConfirmationWindow(Adw.Window):
    - _update_diff_view(full) -> renders context-aware or full-file diff.

### [FILE: log_viewer.py] [STUB]
Role: Syntax-highlighted journal log viewer for zram-setup services.

/DNA/: [call:journal.list_zram_logs() -> loop:render:Gtk.TextTag -> weight:Pango.Weight.BOLD]

- SrcDeps: modules.journal, core.device_management.prober
- SysDeps: gi.repository{Gtk, Adw, Pango}

API:
  - LogViewerDialog(Adw.Window):
    - _load_logs() -> fetches and color-codes the latest 50 log entries per device.

### [FILE: tune_page.py] [STUB]
Role: UI skeleton for kernel memory tuning parameters.

/DNA/: [Gtk.Template(tune_page.ui) -> Adw.Bin]

- SysDeps: gi.repository{Gtk, Adw}

API:
  - TunePage(Adw.Bin): Controller for kernel tunables (e.g., swappiness, watermark_boost_factor).
