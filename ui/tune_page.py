#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import os
from core import boot_config
from core.utils import kernel_cmdline


def get_ui_path(file_name):
    return os.path.join(os.path.dirname(__file__), file_name)


@Gtk.Template(filename=get_ui_path('tune_page.ui'))
class TunePage(Adw.Bin):
    """
    The page for tuning system kernel parameters related to ZRAM performance.
    This class is the Python backend for the tune_page.ui template.
    """
    __gtype_name__ = 'TunePage'

    performance_profile_switch = Gtk.Template.Child()
    vfs_cache_row = Gtk.Template.Child()
    psi_cpu_switch = Gtk.Template.Child()
    psi_memory_switch = Gtk.Template.Child()
    psi_io_switch = Gtk.Template.Child()
    disable_zswap_button = Gtk.Template.Child()
    zswap_warning_banner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        """Initializes the TunePage widget."""
        super().__init__(**kwargs)
        self._loaded = False
        
        # Connect signals
        self.performance_profile_switch.connect("notify::active", self._on_performance_profile_toggled)
        self.vfs_cache_row.connect("notify::value", self._on_vfs_cache_changed)
        self.psi_cpu_switch.connect("notify::active", self._on_psi_toggled)
        self.psi_memory_switch.connect("notify::active", self._on_psi_toggled)
        self.psi_io_switch.connect("notify::active", self._on_psi_toggled)
        self.disable_zswap_button.connect("clicked", self._on_disable_zswap_clicked)

    def lazy_load(self):
        if self._loaded:
            return
        self._loaded = True
        self._refresh_state()

    def _refresh_state(self):
        """Syncs UI switches with current system state."""
        self._is_refreshing = True
        
        # 1. Performance Profile
        swappiness = boot_config.get_swappiness()
        if swappiness == 180:
            self.performance_profile_switch.set_active(True)
            
        # 2. VFS Cache Pressure
        try:
            from core.utils.common import read_file
            val = read_file("/proc/sys/vm/vfs_cache_pressure")
            if val:
                self.vfs_cache_row.set_value(int(val))
        except:
            pass
            
        # 3. PSI
        self.psi_cpu_switch.set_active(kernel_cmdline.is_kernel_param_active("psi=1"))
        # (Assuming memory/io also follow psi=1 for now, or specific probes)
        self.psi_memory_switch.set_active(kernel_cmdline.is_kernel_param_active("psi=1"))
        self.psi_io_switch.set_active(kernel_cmdline.is_kernel_param_active("psi=1"))
        
        # 4. ZSwap
        if kernel_cmdline.is_kernel_param_active("zswap.enabled=0"):
            self.disable_zswap_button.set_sensitive(False)
            self.disable_zswap_button.set_label("Disabled")
            
        self._is_refreshing = False

    def _on_performance_profile_toggled(self, row, param):
        if getattr(self, '_is_refreshing', False):
            return
        active = row.get_active()
        boot_config.apply_sysctl_profile(active)

    def _on_vfs_cache_changed(self, row, param):
        if getattr(self, '_is_refreshing', False):
            return
        val = int(row.get_value())
        boot_config.apply_sysctl_values({"vm.vfs_cache_pressure": str(val)})

    def _on_psi_toggled(self, row, param):
        if getattr(self, '_is_refreshing', False):
            return
        active = row.get_active()
        # This only writes the GRUB config, requires update-grub
        boot_config.set_psi_in_grub(active)
        self.zswap_warning_banner.set_revealed(True)
        self.zswap_warning_banner.set_title("⚠️ PSI Change: Reboot & update-grub required!")

    def _on_disable_zswap_clicked(self, btn):
        boot_config.set_zswap_in_grub(False)
        self.zswap_warning_banner.set_revealed(True)
        self.zswap_warning_banner.set_title("⚠️ ZSwap Disabled: Reboot & update-grub required!")
