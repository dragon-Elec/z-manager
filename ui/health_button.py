#!/usr/bin/env python3
# zman/ui/health_button.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

from enum import Enum
from typing import Optional

class HealthState(Enum):
    """Represents the overall system health state."""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"

class HealthStatusButton(Gtk.Button):
    """
    A compact icon button that displays the current system health status.
    Shows state via icon color and tooltip. Opens detailed report when clicked.
    """
    
    __gtype_name__ = 'HealthStatusButton'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._current_state = HealthState.UNKNOWN
        
        # Make it a simple icon button
        self.set_has_frame(True)
        self.set_valign(Gtk.Align.CENTER)
        
        # Icon
        self._icon = Gtk.Image()
        self._icon.set_pixel_size(20)
        self.set_child(self._icon)
        
        # Set initial state
        self.set_state(HealthState.UNKNOWN)
    
    def set_state(self, state: HealthState, subtitle: Optional[str] = None):
        """
        Updates the button appearance based on health state.
        
        Args:
            state: The current health state
            subtitle: Optional subtitle for tooltip
        """
        self._current_state = state
        
        # Remove previous state classes
        for s in HealthState:
            self.remove_css_class(f"health-{s.value}")
        
        # Apply new state class for styling
        self.add_css_class(f"health-{state.value}")
        
        # Update icon and tooltip based on state
        if state == HealthState.HEALTHY:
            self._icon.set_from_icon_name("emblem-ok-symbolic")
            tooltip = "System Optimal"
            if subtitle:
                tooltip += f"\n{subtitle}"
        elif state == HealthState.WARNING:
            self._icon.set_from_icon_name("dialog-warning-symbolic")
            tooltip = "Attention Needed"
            if subtitle:
                tooltip += f"\n{subtitle}"
            else:
                tooltip += "\nPerformance optimization available"
        elif state == HealthState.ERROR:
            self._icon.set_from_icon_name("dialog-error-symbolic")
            tooltip = "Issues Detected"
            if subtitle:
                tooltip += f"\n{subtitle}"
            else:
                tooltip += "\nAction required"
        else:  # UNKNOWN
            self._icon.set_from_icon_name("emblem-system-symbolic")
            tooltip = "Checking System..."
        
        self.set_tooltip_text(tooltip)
    
    def get_state(self) -> HealthState:
        """Returns the current health state."""
        return self._current_state

