# WebKitGTK & Wayland Rendering Notes

This document captures known rendering anomalies, causes, and workarounds for the WebKitGTK frontend container running under GNOME 46 (Wayland) on Intel HD Graphics 5500 (Broadwell) and similar hardware.

## 1. Blurry Text During Scrolling
*   **Symptom:** Text and icons inside scrolling containers or grid structures become blurry during or after scrolling, and snap back to crispness only on window resize or layout mutation (e.g., expanding cards).
*   **Root Cause:** Continuous high-precision scroll offsets (emitted natively by Wayland input streams) stop at fractional coordinates (e.g. `12.33px`). WebKitGTK promotes these scrollable containers to GPU compositing layers (textures). The GPU's bilinear filter interpolates the texture across physical pixels, blurring the text.
*   **Resolution:**
    *   **CSS Pixel Snapping:** Force elements to align to integer bounds using:
        ```css
        .card, .card-widget {
          backface-visibility: hidden;
          -webkit-backface-visibility: hidden;
          transform: translate3d(0, 0, 0);
          contain: paint layout;
          box-sizing: border-box;
        }
        ```
    *   **Disable Smooth Scroll:** Disable WebKitGTK's internal smooth scroll interpolation to snap the scroll offset strictly to whole pixels:
        ```python
        settings.set_enable_smooth_scrolling(False)
        ```

## 2. Wayland Fractional Scaling & Compositor Conflicts
*   **Symptom:** Blank screens, severe flickering, or layout shifts on Wayland displays.
*   **Root Cause:** WebKitGTK's DMA-BUF renderer (which shares zero-copy GPU buffers between the WebProcess and UIProcess) frequently conflicts with older Mesa drivers (e.g. Broadwell GT2) or proprietary NVIDIA drivers.
*   **Resolution:**
    *   Set environment variables at early startup to force integer alignment and bypass buffer-sharing driver bugs:
        ```python
        import os
        os.environ["GDK_DEBUG"] = "gl-no-fractional"
        os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
        ```

## 3. Font Antialiasing Flicker
*   **Symptom:** Font weights look inconsistent or flicker between thick subpixel rendering and thin grayscale rendering.
*   **Root Cause:** Accelerated GPU layers do not reliably support subpixel (LCD) antialiasing.
*   **Resolution:** Force consistent grayscale antialiasing on WebKit-based renderers:
    ```css
    html, body {
      -webkit-font-smoothing: subpixel-antialiased;
    }
    ```
