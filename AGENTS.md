# Z-Manager Agent Instructions

This document outlines key technical decisions, environment constraints, and development guidelines for agents working on the Z-Manager repository.

## Developer Workflows & Commands

- **Run Tauri (Primary Dev Mode):** Run `pnpm tauri dev` inside the `webUI/` directory.
- **Build Tauri (Production):** Run `pnpm tauri build` inside the `webUI/` directory.
- **Run PyGObject Shell (Legacy Dev Mode):**
  1. Start Vite dev server: `cd webUI && pnpm dev`
  2. Run wrapper in dev mode: `ZMAN_DEV=1 python3 webUI/server.py`
- **Build Frontend Assets:** Run `pnpm build` inside the `webUI/` directory.
- **Run Python Unit Tests:** Run `pytest` in the root directory. Tests mock privileged commands (e.g., `detect_bootloader`) and `systemd.journal` to prevent sudo prompts.

## Architecture & IPC

- **Dual-Mode Shell Architecture:** The application can run under a Tauri Rust shell (primary) or a PyGObject/Gjs shell (legacy).
- **Port-Free Stdio IPC:**
  - The backend sidecar (`webUI/sidecar.py`) runs in Stdio IPC mode (no `--port` argument) when spawned by the shell.
  - **Telemetry (Python -> JS):** The sidecar prints line-delimited JSON telemetry to `stdout`. The shell reads these lines and forwards them to the webview (via Tauri events or `window.onPythonMessage`).
  - **Commands (JS -> Python):** The frontend sends commands to the shell (via Tauri `invoke` or WebKit `postMessage`), which writes them to the sidecar's `stdin`.
  - **Standard Stream Rules:** Since `stdout` is reserved strictly for JSON lines, all sidecar logging, warnings, and tracebacks **must** go to `sys.stderr` to avoid stream corruption.
  - **Line-Buffering:** The sidecar must explicitly call `sys.stdout.flush()` after every JSON line.
  - **Request-Response Matching:** The sidecar preserves `requestId` from the request payload in the response payload to allow Promise-based matching in the frontend bridge (`webUI/src/lib/bridge.ts`).

## WebKitGTK & Wayland Rendering Constraints

- **Scroll-Blur & Fractional Rendering Fixes:**
  - WebKitGTK on Wayland can cause text/icon blurriness if elements rest on fractional coordinates.
  - **Environment Variables:** The Rust and Python shells set `GDK_DEBUG=gl-no-fractional` (forces integer pixel alignment) and `WEBKIT_DISABLE_DMABUF_RENDERER=1` (bypasses buffer-sharing driver bugs on Wayland while keeping hardware acceleration fully enabled).
  - **CSS Containment:** Card containers must use `contain: paint layout;` and `box-sizing: border-box;` to prevent flexbox fractional coordinate bleed.
  - **Smooth Scrolling:** Smooth scrolling is enabled (`set_enable_smooth_scrolling(true)`) for a native feel; the GDK env vars and CSS containment are sufficient to prevent blur.

## Frontend UI & Build Rules

- **UI Stack:** Svelte 5 (Runes), Vite 8, Tailwind CSS 4.3, DaisyUI 5.
- **Vite Plugin Order:** In `webUI/vite.config.ts`, `svelte()` **must** be placed before `tailwindcss()`. Otherwise, Tailwind will attempt to parse raw Svelte source code as CSS, throwing `Invalid declaration` errors.
- **Tauri API Imports:** Do **not** import `@tauri-apps/api` statically in frontend files. It will crash the app with a `TypeError` in non-Tauri environments (like the PyGObject shell or standard browsers). Use dynamic imports guarded by `window.__TAURI_INTERNALS__ !== undefined` (see `webUI/src/lib/bridge.ts`).
- **Component Stack Strategy (DaisyUI 5 + Bits UI):**
  - Use native DaisyUI components and default themes.
  - Use portal-based, dynamically positioned headless components from **Bits UI** for menus, tooltips, dropdowns, and modals to prevent viewport clipping.
  - **Tooltip Provider Rule:** Tooltip components require a top-level `<Tooltip.Provider>` wrapping the app container in `App.svelte` to prevent runtime startup crashes.
- **State Mutation & Effect Safe Zones:**
  - Wrap state modifications inside Svelte 5's `untrack` function when reading and mutating `$state` objects within the same `$effect` block to prevent `effect_update_depth_exceeded` runtime errors.
