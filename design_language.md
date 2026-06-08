# Z-Manager Design Language

> **Philosophy:** Calm Control  
> **Aesthetic:** Grainy Earthed Glassmorphism  
> **Principle:** The system is the interface.

---

## 1. Design Philosophy: "Calm Control"

Z-Manager governs something most users never think about — memory pressure, swap tiers, hibernation safety. The interface should feel like a **calm, confident control surface**. Not a dashboard full of flashing alerts. More like a thermostat than a car dashboard.

The app doesn't show you *data*. It shows you the **health of your system** — and lets you act on it without leaving the view you're in.

### Core UX Axioms

| Axiom | Meaning |
|---|---|
| **One Surface** | There are no pages. The dashboard IS the app. Everything unfolds in place. |
| **Progressive Disclosure** | Show the minimum needed at rest. Reveal depth on interaction. |
| **Contextual Configuration** | Settings live next to the data they affect. No "settings page." |
| **System as Organism** | The UI breathes. Metrics pulse. Pressure is felt, not read. |
| **Calm by Default, Urgent When Needed** | Green silence. Amber whispers. Red speaks. |

---

## 2. Information Architecture: The Memory Topology

Instead of a traditional app with sidebar navigation (Dashboard → ZRAM → Hibernation → Logs), Z-Manager presents a **single living map of the system's memory topology**.

### The Three Tiers (Visual Hierarchy)

The system has a natural hierarchy that maps directly to visual layout:

```
┌─────────────────────────────────────────────┐
│                 HOT TIER                     │
│            RAM + ZRAM (Priority 100)         │
│         Fast · Volatile · Compressed         │
├─────────────────────────────────────────────┤
│                COLD TIER                     │
│           Disk Swap (Priority 0)             │
│        Slow · Persistent · Hibernate         │
├─────────────────────────────────────────────┤
│              SYSTEM PRESSURE                 │
│          PSI · Governor · Tunables           │
│        The forces acting on the tiers        │
└─────────────────────────────────────────────┘
```

This isn't a diagram — it's the actual layout metaphor. The dashboard cards are organized by thermal metaphor: hot at top, cold at bottom, pressure surrounding everything.

### Why No Pages?

| Traditional App | Z-Manager |
|---|---|
| "Go to Hibernation page" | Expand the cold tier card — hibernation config unfolds inline |
| "Go to ZRAM settings page" | Tap a ZRAM device in the hot tier — config panel slides out |
| "Go to Tuning page" | Sliders are always visible in the pressure zone |
| "Go to Logs page" | Contextual log snippets appear when something goes wrong |

Navigation is replaced by **depth**. You don't go *somewhere else*. You go *deeper into what you're looking at*.

---

## 3. Dashboard Anatomy

The dashboard is a responsive **Bento Grid** — but not an arbitrary grid of unrelated cards. Each card represents a **zone** in the memory topology.

### Zone A: The Orb (System Heartbeat)

The hero element. A single circular gauge (the ZramGauge) that communicates overall system health at a glance.

- **At rest:** Shows compression ratio, total ZRAM usage, active algorithm.
- **Under pressure:** The gauge color shifts from green → amber → red as memory pressure increases. The arc animation feels like breathing — slow and steady when healthy, rapid when stressed.
- **On interaction:** Expanding the orb reveals per-device breakdown. Each ZRAM device becomes its own mini-gauge with inline configuration.

The orb is both **status indicator** and **entry point** to ZRAM device management. No separate page needed.

### Zone B: Cold Tier (Hibernate & Disk Swap)

A card that shows the persistent storage layer — the cold side of Split-Horizon.

- **At rest:** Shows disk swap status, hibernate readiness as a simple badge (Ready / Not Ready / Partial), and available swap space.
- **Under pressure:** If hibernate readiness fails a check, the relevant badge pulses softly — it doesn't scream. The badge tooltip (Bits UI portal) explains exactly what's wrong.
- **On interaction:** Expanding the card unfolds the full hibernation configuration:
  - **Readiness Checklist:** ZRAM coexistence ✓, Swap size fitness ✓, Secure boot status ✓, Resume parameters ✓
  - **Swap Manager:** Create/resize swap storage, select backing partition
  - **Power Policy:** Lid close behavior, hibernate delay slider
  - **Boot Config:** Current resume parameters, "Apply & Regenerate Initramfs" action

Hibernation is not a destination. It's a **property of the cold tier** that unfolds when you need it.

### Zone C: System Pressure (The Forces)

Real-time PSI (Pressure Stall Information) sparklines — the nervous system of the machine.

- **At rest:** Three compact sparklines (Memory, CPU, I/O) showing the last 60 seconds. Calm and minimal.
- **Under pressure:** Sparklines that enter warning territory shift color. The card doesn't shout — the data speaks.
- **On interaction:** Hovering reveals exact values. Expanding could show historical trends (if we buffer data).

This zone provides **context** for everything else. If memory pressure is high, the orb will be amber, and this card explains *why*.

### Zone D: Quick Tuning (The Dials)

Always-visible controls that affect system behavior in real time.

- **vm.swappiness:** Slider (0–200). The single most impactful ZRAM tunable.
- **vm.vfs_cache_pressure:** Slider for directory/inode cache behavior.
- **CPU Governor:** Dropdown selector (powersave / performance / schedutil).

These are **ambient controls** — always accessible, no drill-down needed. They use optimistic UI: slide, apply immediately, rollback gracefully on failure.

### Zone Layout (Responsive)

```
Desktop (≥1024px):
┌──────────┬──────────┐
│  Zone A  │  Zone B  │
│  (Orb)   │  (Cold)  │
├──────────┼──────────┤
│  Zone C  │  Zone D  │
│ (Pressure)│ (Tuning) │
└──────────┴──────────┘

Tablet / Narrow (< 1024px):
┌──────────────────────┐
│       Zone A         │
├──────────────────────┤
│       Zone B         │
├──────────────────────┤
│       Zone C         │
├──────────────────────┤
│       Zone D         │
└──────────────────────┘
```

---

## 4. Shell: Minimal Chrome

Since the dashboard IS the app, the shell is intentionally minimal. No sidebar. No tab bar. Just enough chrome to frame the content.

### Top Bar (Title Strip)

A single thin strip across the top:

```
┌─────────────────────────────────────────────────────────┐
│  ● Z-Manager    2 devices · 16GB · Hibernate Ready   ⚙ │
└─────────────────────────────────────────────────────────┘
```

- **Left:** App name with a colored status dot (green = healthy, amber = pressure, red = critical).
- **Center:** System summary string — a single sentence that tells you everything at a glance. Dynamically generated: `"{n} ZRAM devices · {ram} RAM · {hibernate_status}"`.
- **Right:** Settings gear icon (opens a Bits UI sheet/drawer for theme selection, sidecar connection status, about info).

### Why No Sidebar?

A sidebar implies multiple destinations. Z-Manager has **one destination with multiple depths**. A sidebar would:
- Waste 200–250px of horizontal space in a utility app
- Suggest that the user needs to "go somewhere" to do something
- Fragment the topology into disconnected pages

The top bar gives identity and context. The grid gives everything else.

### Bottom Status Line (Optional, Subtle)

A subtle, low-contrast line at the very bottom:

```
┌─────────────────────────────────────────────────────────┐
│  SSE Connected · Last update 2s ago      v0.9.0-beta   │
└─────────────────────────────────────────────────────────┘
```

Only visible for diagnostics. Could be hidden by default and toggled from settings.

---

## 5. Interaction Patterns

### 5.1 Progressive Disclosure (Expand-in-Place)

Cards have two states: **resting** and **expanded**.

- **Resting:** Compact summary. Metric + badge + one-line status.
- **Expanded:** Full detail panel slides open below the summary. Configuration controls, checklists, actions.
- **Transition:** Smooth height animation. No page change, no modal, no route switch.

Only one card can be expanded at a time (accordion behavior) — or we allow multiple if the viewport is tall enough. TBD based on testing.

### 5.2 Optimistic UI with Graceful Rollback

Any mutation (slider change, toggle, button press):
1. **Immediately** update the UI control to the new state.
2. Show a subtle loading indicator (spinning icon, pulsing border).
3. Send the command to the sidecar via HTTP POST.
4. **On success:** Remove loading indicator. Done.
5. **On failure:** Revert UI state. Show a toast notification explaining what went wrong (e.g., "Polkit authentication cancelled").

### 5.3 Hazard Zones (Confirmation Dialogs)

Read-only displays have **zero friction**. You can look at anything instantly.

Mutations are tiered:

| Tier | Action Type | Friction |
|---|---|---|
| **Low** | Tunable sliders (swappiness, cache pressure) | None — optimistic apply |
| **Medium** | Governor change, ZRAM algorithm change | Inline confirmation ("Apply?") |
| **High** | Reset ZRAM device, create swap, modify hibernation boot config | Portal-based confirmation dialog (Bits UI) with explicit "I understand" |

### 5.4 Contextual Micro-Logs

Instead of a dedicated "Logs" page, relevant log entries appear **inline** when something goes wrong. Example:

- ZRAM device fails to reset → The device card shows a collapsed "Last error" section with the relevant `journalctl` output.
- Hibernation readiness check fails → The failing badge shows a "Why?" link that expands to show the diagnostic.

Full journal access can live behind a settings panel or an expandable drawer — but it's not a primary navigation target.

---

## 6. Visual Language: "Grainy Earthed Glassmorphism"

### 6.1 Surfaces

Every card is a frosted glass panel floating above the background canvas.

```css
/* Card surface */
background: oklch(from var(--color-base-100) l c h / 0.6);
backdrop-filter: blur(16px);
border: 1px solid oklch(from var(--color-base-content) l c h / 0.08);
border-radius: var(--radius-box);
```

Cards have **depth** — they float. Active/expanded cards come slightly forward (subtle shadow increase).

### 6.2 Background Canvas

The root background uses a dark base with soft aurora gradient accents:

- **Dark mode:** Deep charcoal (`base-300`) with subtle radial gradient blooms in muted green and amber (Gruvbox palette).
- **Light mode:** Warm off-white with soft pastel gradient accents.

The gradients are static or very slowly animated — they set mood, not distract.

### 6.3 Noise / Grain Texture

A global SVG noise filter overlay at very low opacity:

```css
/* Global grain overlay — applied once on the root */
.grain::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.015;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,..."); /* tiny noise SVG */
}
```

This kills the "plastic digital" feel and adds tactile warmth. It's barely visible but felt.

### 6.4 Color Semantics

Colors are not decorative — they carry meaning:

| Semantic | Gruvbox Token | Meaning |
|---|---|---|
| `success` / green | `--color-success` | Healthy, compressed, efficient |
| `warning` / amber | `--color-warning` | Pressure building, attention needed |
| `error` / red | `--color-error` | Critical, action required |
| `info` / blue | `--color-info` | Cold tier, persistent, informational |
| `base` | `--color-base-*` | Surfaces, backgrounds, neutral content |
| `primary` | `--color-primary` | Interactive elements, CTAs |

The dashboard should be **mostly neutral** (base colors) with **semantic color accents** that draw attention only where needed. A healthy system should look calm and monochromatic. Color appears when something needs attention.

### 6.5 Typography

- **Font:** System sans-serif stack (Inter if available, else SF Pro / system default).
- **Metrics:** Large, light-weight numbers. `text-3xl font-light` for headline values.
- **Labels:** Small, muted, uppercase tracking. `text-xs uppercase tracking-wider text-base-content/50`.
- **Hierarchy:** Numbers > Labels > Descriptions. The eye hits the metric first, then the label, then the explanation.

### 6.6 Motion

All transitions should feel organic and unhurried:

- **Card expand/collapse:** 300ms ease-out height transition.
- **Gauge arcs:** Svelte spring stores with moderate damping (stiffness: 0.1, damping: 0.7) — mechanical dial feel.
- **Value changes:** Numbers count up/down smoothly, not snap.
- **Avoid:** Bouncy springs, fast snaps, parallax, anything that feels "web-appy."
- **Rule:** If WebKitGTK drops a frame, the animation is too complex. Prefer CSS transitions over JS-driven animation.

### 6.7 DaisyUI 5 Effects

DaisyUI 5's built-in `--depth` and `--noise` effect variables align perfectly with this aesthetic:

- **`--depth`:** Enable globally for subtle depth on buttons, toggles, checkboxes.
- **`--noise`:** Enable globally for textured component surfaces.

These are native DaisyUI features — no custom CSS needed.

---

## 7. Component Strategy

### DaisyUI 5 Native (Use Directly)
- `card` — All bento zone containers
- `btn`, `btn-soft`, `btn-dash` — Actions and CTAs
- `badge`, `badge-soft` — Status indicators
- `range` — Tunable sliders (swappiness, cache pressure)
- `select` — Governor dropdown
- `toggle` — Binary switches
- `alert`, `alert-soft` — Inline warnings and errors
- `loading` — Spinners for optimistic UI
- `status` — Live connection/health indicators
- `list` — Expandable detail rows
- `fieldset` + `label` — Configuration form groups
- `validator` — Input validation feedback
- `dock` — Optional bottom status bar

### Bits UI (Portal-Based, Headless)
- **Tooltip** — Sparkline hover values, badge explanations
- **Dialog** — Hazard zone confirmation modals
- **Dropdown Menu** — Theme selector, governor picker (if select clips)
- **Popover** — Contextual info panels
- **Sheet/Drawer** — Settings panel (slides from right)

### Custom Components
- **ZramGauge** — SVG orb with twin-snake arcs (existing, Cairo-proportioned)
- **Sparkline** — Lightweight SVG pressure chart
- **AuroraBackground** — Subtle gradient canvas (CSS only, no JS)
- **GrainOverlay** — SVG noise filter (CSS only)

---

## 8. State Architecture

### Svelte 5 Runes

All state is reactive via Svelte 5 runes:

- **`$state`** — Raw telemetry values from SSE (bytes, device arrays, PSI values).
- **`$derived`** — All formatting and calculations happen client-side:
  - Compression ratio = `origBytes / comprBytes`
  - Swap fitness = `swapFree > (ramUsed - cached) + zramOrigTotal`
  - Pressure severity = thresholds on PSI `some` values
  - System summary string = derived from device count, RAM, hibernate status

### Data Flow

```
Sidecar (Python)
    │
    ├── SSE stream (/events) ──→ $state (raw bytes)
    │                                  │
    │                                  ├──→ $derived (formatted values)
    │                                  │
    │                                  └──→ UI components (reactive)
    │
    └── HTTP POST (/api/action) ←── User interactions
```

No intermediate state stores. No stores file. State lives in the root component and flows down via props. Simple.

---

## 9. Summary: What Makes Z-Manager Feel Different

| What | How |
|---|---|
| **Not a settings app** | It's a living system map you interact with |
| **No navigation** | One surface, progressive disclosure, expand in place |
| **Calm by default** | Neutral at rest, semantic color only when needed |
| **Tactile and warm** | Frosted glass + grain texture + organic motion |
| **Configuration is contextual** | Settings live next to the data they affect |
| **Hibernation is integrated** | It's a property of the cold tier, not a separate page |
| **Desktop-native feel** | Generous radii, restrained type, no web-app-iness |
