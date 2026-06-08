# Z-Manager Agent Instructions

This document outlines key technical decisions, environment constraints, and development guidelines for agents working on the Z-Manager repository.

## Developer Workflows & Commands

- **Build Frontend:** Run `pnpm build` inside the `webUI/` directory to compile the Svelte 5 application.
- **Run Backend/UI (Production Mode):** Run `python3 webUI/server.py` to boot up the application.
- **Run Backend/UI (Development Mode):**
  1. Start the Vite dev server: `cd webUI && pnpm dev`
  2. Run the wrapper in dev mode: `ZMAN_DEV=1 python3 webUI/server.py`
  This enables Hot Module Replacement (HMR) in the WebKitGTK window.

## Architecture

- **Decoupled Sidecar Architecture:** To prevent Python's Global Interpreter Lock (GIL) from blocking the UI rendering thread, the application is split into two processes:
  1. **UI Shell (`webUI/server.py`):** A lightweight PyGObject wrapper that spawns the GTK window and WebKitGTK webview, manages the backend sidecar lifecycle, and handles native IPC.
  2. **Backend Sidecar (`webUI/sidecar.py`):** A pure Python process that handles system telemetry queries, resource management, and mutation commands.
- **IPC Details (Stdio-Based JSON Stream):**
  - **No Network Ports:** The application does not use HTTP, SSE, or TCP sockets. Communication is completely port-free and uses standard output/input streams.
  - **Telemetry (Python -> JS):** The sidecar prints line-delimited JSON telemetry payloads to `stdout` every second. The UI shell reads these lines from the sub-process output stream and natively evaluates them in the webview context via `window.onPythonMessage(data)`.
  - **Commands (JS -> Python):** The frontend dispatches commands natively via `window.webkit.messageHandlers.zmanager.postMessage()`. The UI shell captures these messages in Python and writes the JSON lines to the sidecar's `stdin`.
  - **Standard Stream Rules:** Since `stdout` is reserved strictly for serialized JSON lines, any debug statement, warning, or unhandled traceback in the sidecar **must** be directed to `sys.stderr` to avoid stream corruption.
  - **Line-Buffering:** The sidecar must explicitly call `sys.stdout.flush()` after every JSON line to prevent buffering latency.

## Frontend UI Rules (Strict UI Guidelines)

- **UI Stack:** Svelte 5 (using Runes: `$state`, `$derived`, `$props`), Vite 8, Tailwind CSS 4.3, DaisyUI 5.
- **Component Stack Strategy (DaisyUI 5 + Bits UI):** 
  - Use native DaisyUI components and default styles as much as possible. Keep styling simple and do **not** implement any custom themes; use the default themes provided by DaisyUI.
  - To prevent rigid rendering and viewport clipping errors (e.g., in menus, tooltips, dropdowns, and modals), combine DaisyUI styling with portal-based, dynamically positioned headless components from **Bits UI**.
  - **Tooltip Provider Rule:** Tooltip components require a top-level `<Tooltip.Provider>` wrapping the app container. Without this wrapper, the app will throw a context exception on runtime startup and display a blank window.
  - Do **not** use static CSS-only DaisyUI tooltips (`data-tip`) or rigid overlays which clip near viewport boundaries.
  - If a component or pattern is not natively available in DaisyUI, search the internet using the google search tool to find how to implement it or find standard patterns.
  - Svelte transitions and animations must be layout-stable to avoid dropping frames or causing lag inside WebKitGTK.
- **State Mutation & Effect Safe Zones:**
  - **Avoid Direct State Mutation in Effects:** Reading and mutating Svelte `$state` objects within the same `$effect` block causes circular dependencies. Always wrap state modifications inside Svelte 5's `untrack` function (e.g., in history buffers or reactive telemetry syncs) to prevent `effect_update_depth_exceeded` runtime errors.
- **Glassmorphism & Grain (Future Direction):**
  - Keep the UI simple and clean. If glassmorphism and grain are implemented in later updates, achieve them using standard Tailwind backdrop blur (`backdrop-blur-md`), semi-transparent backgrounds (`bg-base-100/60`), and a global low-opacity SVG noise filter (`opacity-[0.015]` with `mix-blend-overlay`) to avoid heavy custom CSS.
- **ZramGauge Visual Proportions:** 
  - The circular `ZramGauge` widget uses exact 1:1 Cairo canvas proportions: size `156x170`, inner radius `70.2`, line width `9.36`, background/ghost tracks, and precise text vertical positions. Do not alter this geometry.
- **Theme Auto-Detection:** 
  - Detect system dark/light modes automatically using CSS media queries (`prefers-color-scheme`) and apply matching theme tokens. Keep themes clean, readable, and consistent.
- **Build Constraints:** 
  - Vite inlines all assets into a single static file via `vite-plugin-singlefile` for WebKitGTK local loading compatibility. Avoid importing huge binary assets or external URLs directly in Svelte components.

## Dashboard Layout & State Management

- **Bento Grid Layout:** The main dashboard is structured as a bento grid of four specialized cards:
  - **Bento A (ZRAM Live Telemetry):** Holds the circular `ZramGauge` widget (Hero card).
  - **Bento B (System Pressure):** Sparklines showing Memory/CPU/IO pressure trends using PSI (Pressure Stall Information).
  - **Bento C (Hibernate Readiness):** A checklist verifying if ZRAM and hibernation are configured to safely coexist.
  - **Bento D (Quick Tuning):** Quick sysctl sliders (e.g., `vm.swappiness`) and CPU governor selection.
- **State & Calculations:**
  - The backend streams raw bytes. The frontend must use Svelte 5 `$derived` runes to perform all formatting and calculations (e.g., Compression Ratio = `origBytes / comprBytes`) on the client side.
- **Optimistic UI & Hazard Zones:**
  - **Optimistic UI:** When toggling system settings, immediately update the UI control and show a loading state while the backend executes the command. If the command fails (or the user cancels the Polkit password prompt), gracefully revert the UI state and trigger a notification.
  - **Hazard Zones:** Read-only widgets have no friction. Any mutation (e.g., resetting ZRAM or modifying hibernation settings) must require explicit confirmation dialogs (using portal-based dialogs) to prevent accidental misclicks.
