import gi
import math
import cairo

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GObject


class CircularWidget(Gtk.Box):
    """
    A standalone 'Widget' encompassing a circular gauge and a bottom status bar.
    Refactored for robustness: Uses relative positioning instead of hardcoded pixels.
    """
    __gtype_name__ = 'CircularWidget'

    _shared_provider = None

    @classmethod
    def _ensure_shared_styles(cls):
        if cls._shared_provider:
            return cls._shared_provider
            
        cls._shared_provider = Gtk.CssProvider()
        css_data = b"""
            .wb-caption { 
                font-family: "Roboto Condensed", "DIN Alternate", "Arial Narrow", sans-serif;
                font-size: 8pt; 
                font-weight: 300;
                font-stretch: condensed;
                opacity: 0.7; 
            }
            .usage-caption {
                font-family: "Roboto Condensed", "DIN Alternate", "Arial Narrow", sans-serif;
                font-size: 9pt;
                font-weight: 300;
                font-stretch: condensed;
                opacity: 0.9;
            }
            levelbar.thick-bar {
                min-height: 8px;
            }
            levelbar.thick-bar trough {
                min-height: 8px;
                border-radius: 6px;
                padding: 0;
            }
            levelbar.thick-bar block {
                min-height: 8px;
                border-radius: 6px;
                margin-top: 0;
                margin-bottom: 0;
            }
        """
        cls._shared_provider.load_from_data(css_data)
        return cls._shared_provider

    def __init__(self, device_name="zram0", algo="zstd", 
                 used_bytes=0, total_bytes=0, 
                 orig_bytes=0, compr_bytes=0, 
                 physical_ram_total=0,
                 is_swap=True, backing_dev=None, 
                 bd_used=0, bd_limit=0, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        
        # Ensure styles are loaded
        self._style_provider = self._ensure_shared_styles()
        
        self.set_size_request(180, 220) # Reduced by ~20px as requested
        self.add_css_class("card")      # Make it look like a card
        
        # --- Data ---
        self.device_name = device_name
        self.algo = algo
        self.total_bytes = total_bytes
        self.used_bytes = used_bytes # Usage of the device capacity
        
        self.orig_bytes = orig_bytes
        self.compr_bytes = compr_bytes
        self.physical_ram_total = physical_ram_total
        
        # Calculate Efficiency
        self.efficiency = 1.0
        if compr_bytes > 0:
            self.efficiency = orig_bytes / compr_bytes
            
        self.is_swap = is_swap

        # --- Layout ---
        
        # 1. Top Area (Overlay: Circle + Writeback Icon)
        self.top_overlay = Gtk.Overlay()
        self.top_overlay.set_vexpand(True)
        self.top_overlay.set_hexpand(True)
        self.append(self.top_overlay)

        # The Circle (Main Child)
        self.circle_area = Gtk.DrawingArea()
        self.circle_area.set_draw_func(self.draw_circle)
        # Margins ensure the circle doesn't touch edges, 
        # but the Icon (overlay) will sit in the top-left corner of the card area
        self.circle_area.set_margin_top(12)
        self.circle_area.set_margin_bottom(0)
        self.circle_area.set_margin_start(12)
        self.circle_area.set_margin_end(12)
        
        self.top_overlay.set_child(self.circle_area)
        
        # Writeback Icon + Stats (Overlay)
        # Only show if backing_dev is provided (indicating writeback is linked)
        if backing_dev:
            # We use a box to hold Icon + Text
            wb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            wb_box.set_halign(Gtk.Align.START)
            wb_box.set_valign(Gtk.Align.START)
            wb_box.set_margin_start(8)
            wb_box.set_margin_top(8)
            
            # Icon
            wb_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
            wb_icon.set_pixel_size(16)
            wb_icon.set_opacity(0.6)
            wb_box.append(wb_icon)
            
            # Stats Text (if limit > 0)
            if bd_limit > 0:
                # Simplified formatting (reusing _format_size logic manually for brevity)
                s_used = self._format_size(bd_used).replace(" ", "")
                s_limit = self._format_size(bd_limit).replace(" ", "")
                
                txt = f"{s_used}/{s_limit}"
                wb_lbl = Gtk.Label(label=txt)
                wb_lbl.add_css_class("wb-caption") # Use shared class
                wb_lbl.get_style_context().add_provider(self._style_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
                
                wb_box.append(wb_lbl)
                
            wb_box.set_tooltip_text(f"Writeback: {backing_dev}\\nUsage: {self._format_size(bd_used)} / {self._format_size(bd_limit)}")
            self.top_overlay.add_overlay(wb_box)

        # Configure Icon (Top Right)
        # Always visible
        self.cfg_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic")
        self.cfg_icon.set_pixel_size(22) # Increased from 16 to 22
        self.cfg_icon.set_halign(Gtk.Align.END)
        self.cfg_icon.set_valign(Gtk.Align.START)
        self.cfg_icon.set_margin_end(8)
        self.cfg_icon.set_margin_top(8)
        self.cfg_icon.set_opacity(0.4) # Subtle
        self.cfg_icon.set_tooltip_text("Configure Device")
        self.top_overlay.add_overlay(self.cfg_icon)

        # 2. Bottom Usage Area (Horizontal: Bar + Label)
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_box.set_margin_start(12)
        bottom_box.set_margin_end(12)
        bottom_box.set_margin_bottom(12)
        self.append(bottom_box)

        # Stack Container (Text + Bar)
        stack_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        stack_box.set_hexpand(True)
        stack_box.set_valign(Gtk.Align.CENTER)
        
        # 1. Usage Label (Native Widget)
        used_str = self._format_size(used_bytes)
        total_str = self._format_size(total_bytes)
        
        self.usage_text_label = Gtk.Label(label=f"{used_str} / {total_str}")
        self.usage_text_label.set_xalign(0) # Align left
        self.usage_text_label.add_css_class("usage-caption")
        self.usage_text_label.get_style_context().add_provider(self._style_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        
        stack_box.append(self.usage_text_label)

        # 2. Bar Row (Bar + Percentage)
        bar_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Usage Bar
        self.usage_bar = Gtk.LevelBar()
        self.usage_bar.set_min_value(0)
        self.usage_bar.set_max_value(100)
        self.usage_bar.set_hexpand(True) 
        self.usage_bar.set_valign(Gtk.Align.CENTER)
        
        # Calculate usage %
        usage_pct = 0
        if total_bytes > 0:
            usage_pct = (used_bytes / total_bytes) * 100
        self.usage_bar.set_value(usage_pct)

        # Style: Thicken the bar using CSS
        self.usage_bar.add_css_class("thick-bar") 
        self.usage_bar.get_style_context().add_provider(self._style_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        
        bar_row.append(self.usage_bar)
        
        # Usage Label (Right side of bar)
        self.usage_pct_label = Gtk.Label(label=f"{int(usage_pct)}% Full")
        self.usage_pct_label.add_css_class("caption")
        bar_row.append(self.usage_pct_label)
        
        stack_box.append(bar_row)
        
        bottom_box.append(stack_box)

    def update(self, used_bytes, total_bytes, orig_bytes, compr_bytes, physical_ram_total, bd_used=0, bd_limit=0):
        """
        Updates the widget with new statistics without destroying it.
        """
        self.used_bytes = used_bytes
        self.total_bytes = total_bytes
        self.orig_bytes = orig_bytes
        self.compr_bytes = compr_bytes
        self.physical_ram_total = physical_ram_total
        
        # Recalculate Efficiency
        self.efficiency = 1.0
        if compr_bytes > 0:
            self.efficiency = orig_bytes / compr_bytes
            
        # Update Text Label
        used_str = self._format_size(used_bytes)
        total_str = self._format_size(total_bytes)
        self.usage_text_label.set_label(f"{used_str} / {total_str}")
        
        # Update Bar
        usage_pct = 0
        if total_bytes > 0:
            usage_pct = (used_bytes / total_bytes) * 100
        self.usage_bar.set_value(usage_pct)
        self.usage_pct_label.set_label(f"{int(usage_pct)}% Full")
        
        # Redraw Circle
        self.circle_area.queue_draw()
        
        # NOTE: We are NOT updating the Writeback Label dynamically here for simplicity,
        # as it requires structural changes if it wasn't there before.
        # If writeback stats change significantly, the parent should recreate the widget.

    def _get_rgba(self, context, color_name, fallback=(0.5, 0.5, 0.5, 1.0)):
        res, rgba = context.lookup_color(color_name)
        if res:
            return (rgba.red, rgba.green, rgba.blue, rgba.alpha)
        return fallback

    def _format_size(self, size):
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if abs(size) < 1024.0:
                return f"{size:3.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PiB"

    def draw_circle(self, area, cr, width, height, data=None):
        # Configuration
        # Determine strict drawing limits
        size = min(width, height)
        center_x = width / 2
        # Use relative positioning for center_y. 
        # Original was (height / 2) + 1. 1 is negligible, so let's use 50%
        center_y = height / 2 
        
        # Original: radius = (size / 2) - 10
        # 10 is approx 5% of 200.
        padding = size * 0.05
        radius = (size / 2) - padding
        
        # Original: line_width = 12 (approx 6% of 200)
        line_width = size * 0.06

        ctx = self.get_style_context()
        c_bg = self._get_rgba(ctx, "window_fg_color", (0.3, 0.3, 0.3, 0.1))
        c_bg = (*c_bg[:3], 0.1) # Force low opacity for track
        
        c_primary = self._get_rgba(ctx, "accent_bg_color", (0.2, 0.6, 1.0, 1.0))
        c_text = self._get_rgba(ctx, "window_fg_color", (1, 1, 1, 1.0))
        
        # Error color for Danger Zone
        c_error = self._get_rgba(ctx, "error_bg_color", (0.75, 0.11, 0.11, 1.0)) # Adwaita error red
        c_error_faint = (*c_error[:3], 0.3)

        # 1. Background Track
        cr.set_line_cap(cairo.LINE_CAP_ROUND) # Smooth ends
        cr.set_source_rgba(*c_bg)
        cr.set_line_width(line_width)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

        # 2. Arcs (Twin Snake Logic)
        
        limit = self.physical_ram_total if self.physical_ram_total > 0 else 1
        
        # Calculate Angles (0 to 2*PI based on Physical RAM)
        angle_solid = (self.compr_bytes / limit) * 2 * math.pi
        angle_ghost = (self.orig_bytes / limit) * 2 * math.pi
        
        # Danger Check
        is_danger = self.orig_bytes >= limit
        
        if is_danger:
            c_ghost_snake = c_error_faint
            angle_ghost = 2 * math.pi # Full circle for danger
        else:
             c_ghost_snake = (*c_primary[:3], 0.3) # Faint primary
        
        # Draw Snake 2 (Ghost/Original) - Bottom Layer
        # Always starts at 180 (Left, math.pi)
        if angle_ghost > 0:
            cr.set_source_rgba(*c_ghost_snake)
            cr.set_line_width(line_width)
            cr.arc(center_x, center_y, radius, math.pi, math.pi + angle_ghost)
            cr.stroke()
            
        # Draw Snake 1 (Solid/Compressed) - Top Layer
        # Always starts at 180 (Left, math.pi) and overlays Ghost
        if angle_solid > 0:
            cr.set_source_rgba(*c_primary)
            cr.set_line_width(line_width)
            cr.arc(center_x, center_y, radius, math.pi, math.pi + angle_solid)
            cr.stroke()

        # 3. Center Text
        # ROBUST POSITIONING: Use % of height/size instead of pixels
        # Reference height was 200(ish). 
        # Text 1: -10px (Offset from center) -> -5% of size
        # Text 2: +7px  -> +3.5%
        # Text 3: +25px -> +12.5%
        # Text 4: +55px -> +27.5%
        
        # Scaling font sizes:
        # Title: 35px -> 17.5% of size
        # Small: 13px -> 6.5% of size
        # Huge: 25px -> 12.5% of size
        
        f_title = size * 0.175
        # Enforce minimum readability for small text (Swap/Algo)
        # Even on tiny widgets, don't go below 13px (User requested 13-14)
        f_small = max(size * 0.065, 13)
        f_huge = size * 0.125
        
        off_1 = size * -0.05
        off_2 = size * 0.035
        off_3 = size * 0.125
        off_4 = size * 0.275

        # --- A. Device Name (Top) ---
        cr.set_source_rgba(*c_text)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        
        # Use helper to fit text within 85% of the circle width
        # This prevents "zram3-BIG" from overflowing.
        max_width = size * 0.85
        self._draw_text_fit(cr, self.device_name, center_x, center_y + off_1, f_title, max_width)
        
        # --- B. Device Type ---
        type_str = "[SWAP]" if self.is_swap else "[ZRAM]"
        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        # Type is usually short, but let's be safe
        self._draw_text_fit(cr, type_str, center_x, center_y + off_2, f_small, max_width)

        # --- C. Algo ---
        meta_str = f"{self.algo}"
        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL) 
        # Dimming color
        cr.set_source_rgba(c_text[0], c_text[1], c_text[2], 0.6) 
        
        self._draw_text_fit(cr, meta_str, center_x, center_y + off_3, f_small, max_width)

        # --- D. Efficiency ---
        cr.set_source_rgba(*c_text) # Reset to full white/black
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        eff_str = f"{self.efficiency:.1f}x"
        
        self._draw_text_fit(cr, eff_str, center_x, center_y + off_4, f_huge, max_width)

    def _draw_text_fit(self, cr, text, x_center, y_pos, target_font_size, max_width):
        """
        Draws text centered at (x_center, y_pos), scaling the font down
        if the text is wider than max_width.
        """
        cr.set_font_size(target_font_size)
        (x, y, w, h, dx, dy) = cr.text_extents(text)
        
        if w > max_width and w > 0:
            scale = max_width / w
            cr.set_font_size(target_font_size * scale)
            # Re-measure to center correctly
            (x, y, w, h, dx, dy) = cr.text_extents(text)
            
        cr.move_to(x_center - w/2, y_pos)
        cr.show_text(text)

class MemoryTube(Gtk.DrawingArea):
    """
    A horizontal stacked bar chart showing memory distribution.
    [ App Used | ZRAM (Compressed) | Writeback | Free ]
    """
    __gtype_name__ = 'MemoryTube'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_draw_func(self.draw)
        self.set_content_height(40)
        self.set_valign(Gtk.Align.CENTER)
        
        # Stats
        self.app_used = 0  # RAM used by apps (excluded ZRAM)
        self.zram_used = 0 # RAM used by ZRAM
        self.total_ram = 100 # Total Physical RAM

    def update_stats(self, app_used, zram_used, total_ram):
        self.app_used = app_used
        self.zram_used = zram_used
        self.total_ram = total_ram
        self.queue_draw()

    def _get_rgba(self, color_name, fallback=(0.5, 0.5, 0.5, 1.0)):
        context = self.get_style_context()
        res, rgba = context.lookup_color(color_name)
        if res:
            return (rgba.red, rgba.green, rgba.blue, rgba.alpha)
        if res:
            return (rgba.red, rgba.green, rgba.blue, rgba.alpha)
        return fallback

    def _is_dark_theme(self):
        """
        Heuristic: If text color is bright, we are in dark mode.
        """
        r, g, b, _ = self._get_rgba("window_fg_color", (0, 0, 0, 1))
        # Relative luminance (rec. 709)
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance > 0.5

    def draw(self, area, cr, width, height, data=None):
        # Normalize to width
        if self.total_ram <= 0:
            return

        total_px = width
        app_px = (self.app_used / self.total_ram) * total_px
        zram_px = (self.zram_used / self.total_ram) * total_px
        
        # Colors (Material You Style)
        # We generate a full palette from the system accent
        accent_rgba = self._get_rgba("accent_bg_color", (0.2, 0.4, 0.8, 1.0))
        
        # Determine theme mode (Dark/Light)
        is_dark = self._is_dark_theme()
        
        # Simplified Theme (Direct Accent Usage)
        c_app = accent_rgba
        # ZRAM gets same hue but lower opacity/saturation for contrast
        c_zram = (accent_rgba[0], accent_rgba[1], accent_rgba[2], 0.6)


        # Free Space -> Window Background or View Background
        # We want it slightly darker than the window usually.
        c_free = self._get_rgba("card_bg_color", (0.2, 0.2, 0.2, 1.0))
        # Ensure it has some contrast if it matches the background too well
        
        # Rounded background (Free space)
        cr.set_source_rgba(*c_free)
        self._rounded_rect(cr, 0, 0, width, height, 8)
        cr.fill()

        # App Used Bar
        if app_px > 0:
            cr.set_source_rgba(*c_app)
            # If zram exists, flat right side; otherwise rounded
            radius_corners = (8, 0, 0, 8) if zram_px > 0 else (8, 8, 8, 8)
            # Simplified for now: just draw rects, maybe partial round later
            cr.rectangle(0, 0, app_px, height)
            cr.fill()

        # ZRAM Used Bar
        if zram_px > 0:
            cr.set_source_rgba(*c_zram)
            cr.rectangle(app_px, 0, zram_px, height)
            cr.fill()
            
    def _rounded_rect(self, cr, x, y, w, h, r):
        # Basic rounded rect path
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class ScenarioCard(Gtk.ToggleButton):
    """
    A toggle button styled as a 'Choice Card' with icon, title, and description.
    Used for selecting profiles (Desktop / Server / etc).
    """
    __gtype_name__ = 'ScenarioCard'

    def __init__(self, title, description, icon_name, **kwargs):
        super().__init__(**kwargs)
        self.add_css_class("card")
        
        # Enforce a reasonable size for the cards so they fit in a row
        self.set_size_request(160, 180)
        
        # Main Layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_valign(Gtk.Align.CENTER)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(48) # Bigger icon
        box.append(icon)
        
        # Title
        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("heading")
        lbl_title.set_wrap(True)
        lbl_title.set_justify(Gtk.Justification.CENTER)
        box.append(lbl_title)
        
        # Description
        lbl_desc = Gtk.Label(label=description)
        lbl_desc.add_css_class("caption")
        lbl_desc.set_wrap(True)
        lbl_desc.set_justify(Gtk.Justification.CENTER)
        lbl_desc.set_max_width_chars(15) # Force wrapping sooner
        lbl_desc.set_lines(3) # Limit lines
        lbl_desc.set_ellipsize(3) # Ellipsize at end (PANGO_ELLIPSIZE_END=3)
        box.append(lbl_desc)
        
        self.set_child(box)
