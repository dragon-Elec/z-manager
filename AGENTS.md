# Z-Manager Agent Instructions

Technical decisions, environment constraints, and development guidelines.

## Developer Commands

- **Tauri (primary):** `pnpm tauri dev` / `pnpm tauri build` — both run inside `webUI/`.
  `beforeDevCommand` auto-starts Vite; `beforeBuildCommand` auto-builds.
- **PyGObject/WebKitGTK shell (legacy):**
  1. `cd webUI && pnpm dev` (starts Vite dev server)
  2. `ZMAN_DEV=1 python3 webUI/server.py` (opens a GTK4 window with WebKitGTK webview)
- **Frontend-only build:** `pnpm build` in `webUI/` — uses `vite-plugin-singlefile` to produce a self-contained `dist/index.html`.
- **Python unit tests:** `pytest` from root. All privileged system commands are mocked; no root needed. Integration tests targeting real system state are tagged `@pytest.mark.integration`.

## Architecture & IPC

- **Dual-Mode Shell:** Primary = Tauri Rust shell. Legacy = PyGObject/WebKitGTK shell (`server.py`).
- **Port-Free Stdio IPC:** The sidecar (`webUI/sidecar.py`) runs without `--port` when spawned by a shell. With `--port <N>` it starts an HTTP/SSE server (used for browser-based debugging or standalone operation).
- **Telemetry (Python → JS):** Sidecar prints line-delimited JSON to **stdout**. The shell reads these lines and forwards them to the webview (Tauri `sidecar-message` events or `window.onPythonMessage` callback).
- **Commands (JS → Python):** Frontend sends requests through the shell (Tauri `invoke("send_to_sidecar")` or WebKit `postMessage`), which writes to the sidecar's **stdin**.
- **Stdout Rules:** `stdout` is reserved for JSON telemetry lines. All logging, warnings, and tracebacks **must** go to `sys.stderr`. Sidecar calls `sys.stdout.flush()` after every JSON line.
- **Request-Response Matching:** Sidecar preserves `requestId` from the incoming payload in its response, enabling Promise-based matching in `webUI/src/lib/bridge.ts`.
- **Path Discovery (Sidecar):** Sidecar adds the project root to `sys.path` so it can import `core.*` and `modules.*` without pip-installing the package.

## Test Conventions

- **Privileged tests** require `--privileged` flag (checks `os.geteuid() == 0`). Skipped by default without the flag.
- Markers: `@pytest.mark.privileged` (root-required), `@pytest.mark.integration` (real system state, slow).
- Unit tests mock `core.utils.common.read_file` and `core.utils.common.run` via `BaseTestCase.mock_system_calls()`.
- `pytest` collected 151 items (143 pass, 8 skip) as of last run.

## WebKitGTK & Wayland Rendering Constraints

- **Fractional blur fix:** Set `GDK_DEBUG=gl-no-fractional` and `WEBKIT_DISABLE_DMABUF_RENDERER=1` in the environment before importing GTK. Both shells do this at startup.
- **CSS containment:** Cards in scrolling containers need `contain: paint layout;` and `box-sizing: border-box;` to prevent flexbox fractional coordinate bleed.
- **Smooth scrolling:** Both shells enable smooth scrolling (`set_enable_smooth_scrolling(true)`) for native feel. The GDK env vars plus CSS containment prevent the blur that smooth scrolling can trigger on WebKitGTK.

## Frontend Build Rules

- **Stack:** Svelte 5 (Runes), Vite 8, Tailwind CSS 4.3, DaisyUI 5. TypeScript only (no JS).
- **Vite plugin order:** `svelte()` **must** be placed before `tailwindcss()` in `vite.config.ts`. Reversed order causes Tailwind to parse raw Svelte source as CSS and throw `Invalid declaration`.
- **Tauri API imports:** Never import `@tauri-apps/api` statically. Use dynamic imports guarded by `window.__TAURI_INTERNALS__ !== undefined`. See `webUI/src/lib/bridge.ts`.
- **Path alias:** `$lib` maps to `src/lib` in both Vite and tsconfig.
- **Component strategy:** DaisyUI 5 for themed native components (card, badge, range, select, toggle, btn). Bits UI for portal-based menus/tooltips/dialogs to avoid WebKitGTK viewport clipping.
- **Tooltip provider:** Requires `<Tooltip.Provider>` wrapping the app container in `App.svelte` to prevent runtime startup crash.
- **State mutation in effects:** Wrap `$state` reads and mutations inside the same `$effect` block with Svelte 5's `untrack` to prevent `effect_update_depth_exceeded`.
