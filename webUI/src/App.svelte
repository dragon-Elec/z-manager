<script lang="ts">
  import { onMount } from 'svelte';
  import { 
    LayoutDashboard, Gauge, Database, Sliders, Settings, ShieldAlert,
    ChevronLeft, ChevronRight
  } from 'lucide-svelte';
  import { Tooltip } from 'bits-ui';
  
  // Tab Views
  import DashboardTab from './lib/components/DashboardTab.svelte';
  import ZramConfigTab from './lib/components/ZramConfigTab.svelte';
  import HibernationTab from './lib/components/HibernationTab.svelte';
  import TuningTab from './lib/components/TuningTab.svelte';
  
  // Components
  import SettingsDrawer from './lib/components/SettingsDrawer.svelte';
  import ConfirmationModal from './lib/components/ConfirmationModal.svelte';
  
  // Bridge
  import { initSidecarBridge, onPython } from './lib/bridge';

  // Global UI State
  let activeTab = $state<'dashboard' | 'zram' | 'hibernation' | 'tuning'>('dashboard');
  let backendConnected = $state(false);
  let themeMode = $state('system');
  let settingsOpen = $state(false);
  let sidebarExpanded = $state(true);

  // Telemetry Data
  let health = $state<{
    zramctl_available: boolean;
    systemd_available: boolean;
    sysfs_root_accessible: boolean;
    zswap: { available: boolean; enabled: boolean; detail: string };
    journal_available: boolean;
    kernel_version: string;
    devices_summary: string;
    notes: string[];
  }>({
    zramctl_available: true,
    systemd_available: true,
    sysfs_root_accessible: true,
    zswap: { available: false, enabled: false, detail: '' },
    journal_available: true,
    kernel_version: '',
    devices_summary: '',
    notes: []
  });

  let ram = $state({
    total: 0,
    used: 0,
    free: 0,
    shared: 0,
    buff_cache: 0,
    available: 0
  });

  let devices = $state<any[]>([]);
  let swaps = $state<any[]>([]);
  let hibernation = $state({
    ready: false,
    secure_boot: 'disabled',
    swap_total: 0,
    ram_total: 0,
    recommended_swap_bytes: 0,
    message: ''
  });
  let psi = $state<any>({});
  let tuning = $state<any>({
    swappiness: 60,
    vfs_cache_pressure: 100,
    cpu_governor: 'powersave',
    available_governors: []
  });

  // System Themes
  let availableThemes = $state<string[]>([]);
  let systemIsDark = $state(false);

  // Toast System
  let toast = $state<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  let toastTimeout: any;

  function showToast(type: 'success' | 'error' | 'info', message: string) {
    if (toastTimeout) clearTimeout(toastTimeout);
    toast = { type, message };
    toastTimeout = setTimeout(() => {
      toast = null;
    }, 4000);
  }

  // Confirmation Modal State
  let confirmOpen = $state(false);
  let confirmTitle = $state('');
  let confirmDesc = $state('');
  let confirmCallback = $state<(() => void) | null>(null);

  function requestConfirmation(title: string, desc: string, callback: () => void) {
    confirmTitle = title;
    confirmDesc = desc;
    confirmCallback = () => callback();
    confirmOpen = true;
  }

  onMount(() => {
    // Initialize standard sidecar bridge if window.webkit is not present (standalone dev)
    if (typeof window !== 'undefined' && !window.webkit?.messageHandlers?.zmanager) {
      initSidecarBridge(8000);
    }

    // Load sidebar expansion state
    sidebarExpanded = localStorage.getItem('sidebar-expanded') !== 'false';

    // Lock pinch-to-zoom gestures
    document.addEventListener('touchmove', (event) => {
      if (event.touches.length > 1) {
        event.preventDefault();
      }
    }, { passive: false });

    document.addEventListener('wheel', (event) => {
      if (event.ctrlKey) {
        event.preventDefault();
      }
    }, { passive: false });

    // Read system dark mode preference
    if (typeof window !== 'undefined') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      systemIsDark = media.matches;
      media.addEventListener('change', (e) => {
        systemIsDark = e.matches;
      });
      themeMode = localStorage.getItem('theme-mode') || 'system';
    }

    // Parse available themes dynamically from css rules
    try {
      const themes = new Set<string>();
      for (const sheet of Array.from(document.styleSheets)) {
        try {
          for (const rule of Array.from(sheet.cssRules)) {
            if (rule instanceof CSSStyleRule && rule.selectorText.includes('[data-theme=')) {
              const match = rule.selectorText.match(/\[data-theme=["']?([^"']+)["']?\]/);
              if (match && match[1]) {
                themes.add(match[1]);
              }
            }
          }
        } catch (e) {}
      }
      availableThemes = Array.from(themes).sort();
    } catch (e) {
      console.error("[Theme] Failed to parse themes from stylesheet:", e);
    }

    // Bind sidecar telemetry events
    onPython('dashboard_update', (data) => {
      backendConnected = true;
      if (data.health) health = data.health;
      if (data.ram) ram = data.ram;
      if (data.devices) devices = data.devices;
      if (data.swaps) swaps = data.swaps;
      if (data.hibernation) hibernation = data.hibernation;
      if (data.psi) psi = data.psi;
      if (data.tuning) tuning = data.tuning;
    });

    onPython('connection_status', (connected) => {
      backendConnected = connected;
    });

    return () => {
      if (toastTimeout) clearTimeout(toastTimeout);
    };
  });

  // Theme resolution logic
  let activeTheme = $derived.by(() => {
    if (themeMode === 'system') {
      return systemIsDark ? 'nord-dark' : 'nord';
    }
    if (themeMode === 'dark') {
      return 'nord-dark';
    }
    if (themeMode === 'light') {
      return 'nord';
    }
    return themeMode;
  });

  $effect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', activeTheme);
    }
  });

  function handleConfigureDevice(name: string) {
    activeTab = 'zram';
  }

  function toggleSidebar() {
    sidebarExpanded = !sidebarExpanded;
    localStorage.setItem('sidebar-expanded', String(sidebarExpanded));
  }

  // Sidebar dot color class
  let healthDotClass = $derived.by(() => {
    if (!health.sysfs_root_accessible || !health.systemd_available) {
      return 'bg-error';
    }
    if (health.notes.length > 0 || health.zswap.enabled) {
      return 'bg-warning';
    }
    return 'bg-primary';
  });
</script>

<Tooltip.Provider>
<!-- Lock viewport height to h-screen and prevent parent scrolling -->
<div class="flex flex-row h-screen max-h-screen overflow-hidden bg-base-100 text-base-content relative z-10">
  
  <!-- Sidebar Navigation (Resizable: w-44 or w-14) -->
  <aside class="h-full bg-base-200 border-r border-base-content/10 p-3 flex flex-col justify-between shrink-0 select-none transition-all duration-300 {sidebarExpanded ? 'w-44' : 'w-14 items-center'}">
    <div class="flex flex-col gap-4 w-full">
      <!-- Sidebar Header -->
      {#if sidebarExpanded}
        <div class="flex items-center justify-between px-1 py-2 w-full">
          <div class="flex items-center gap-2.5">
            <span class="w-3 h-3 rounded-full {healthDotClass} transition-colors duration-500 shadow-sm shrink-0"></span>
            <h1 class="text-lg font-bold tracking-tight font-sans">Z-Manager</h1>
          </div>
          <button class="btn btn-2xs btn-ghost btn-circle text-base-content/50 hover:text-base-content" onclick={toggleSidebar} aria-label="Collapse Sidebar">
            <ChevronLeft size={14} />
          </button>
        </div>
      {:else}
        <div class="flex flex-col items-center gap-3 py-2 w-full">
          <span class="w-3 h-3 rounded-full {healthDotClass} transition-colors duration-500 shadow-sm"></span>
          <button class="btn btn-2xs btn-ghost btn-circle text-base-content/50 hover:text-base-content" onclick={toggleSidebar} aria-label="Expand Sidebar">
            <ChevronRight size={14} />
          </button>
        </div>
      {/if}
      
      <!-- Navigation Menu -->
      <ul role="tablist" class="menu p-0 gap-1 text-sm w-full">
        <!-- Dashboard Tab -->
        <li>
          {#if sidebarExpanded}
            <button 
              role="tab"
              class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'dashboard' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
              onclick={() => activeTab = 'dashboard'}
            >
              <LayoutDashboard size={16} /> Dashboard
            </button>
          {:else}
            <Tooltip.Root>
              <Tooltip.Trigger 
                role="tab"
                class="btn btn-sm flex items-center justify-center rounded-xl p-0 transition-all w-8 h-8 min-h-0 border-0 {activeTab === 'dashboard' ? 'bg-primary text-primary-content hover:bg-primary' : 'bg-transparent text-base-content/70 hover:bg-base-300/50 hover:text-base-content'}"
                onclick={() => activeTab = 'dashboard'}
              >
                <LayoutDashboard size={16} />
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content class="z-50 rounded-xl border border-base-content/10 bg-neutral text-neutral-content px-3 py-1.5 text-xs shadow-lg" side="right">
                  Dashboard
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          {/if}
        </li>

        <!-- ZRAM Config Tab -->
        <li>
          {#if sidebarExpanded}
            <button 
              role="tab"
              class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'zram' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
              onclick={() => activeTab = 'zram'}
            >
              <Gauge size={16} /> ZRAM Config
            </button>
          {:else}
            <Tooltip.Root>
              <Tooltip.Trigger 
                role="tab"
                class="btn btn-sm flex items-center justify-center rounded-xl p-0 transition-all w-8 h-8 min-h-0 border-0 {activeTab === 'zram' ? 'bg-primary text-primary-content hover:bg-primary' : 'bg-transparent text-base-content/70 hover:bg-base-300/50 hover:text-base-content'}"
                onclick={() => activeTab = 'zram'}
              >
                <Gauge size={16} />
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content class="z-50 rounded-xl border border-base-content/10 bg-neutral text-neutral-content px-3 py-1.5 text-xs shadow-lg" side="right">
                  ZRAM Configuration
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          {/if}
        </li>

        <!-- Hibernation Tab -->
        <li>
          {#if sidebarExpanded}
            <button 
              role="tab"
              class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'hibernation' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
              onclick={() => activeTab = 'hibernation'}
            >
              <Database size={16} /> Hibernation
            </button>
          {:else}
            <Tooltip.Root>
              <Tooltip.Trigger 
                role="tab"
                class="btn btn-sm flex items-center justify-center rounded-xl p-0 transition-all w-8 h-8 min-h-0 border-0 {activeTab === 'hibernation' ? 'bg-primary text-primary-content hover:bg-primary' : 'bg-transparent text-base-content/70 hover:bg-base-300/50 hover:text-base-content'}"
                onclick={() => activeTab = 'hibernation'}
              >
                <Database size={16} />
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content class="z-50 rounded-xl border border-base-content/10 bg-neutral text-neutral-content px-3 py-1.5 text-xs shadow-lg" side="right">
                  Hibernation
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          {/if}
        </li>

        <!-- Tuning Tab -->
        <li>
          {#if sidebarExpanded}
            <button 
              role="tab"
              class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'tuning' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
              onclick={() => activeTab = 'tuning'}
            >
              <Sliders size={16} /> Tuning
            </button>
          {:else}
            <Tooltip.Root>
              <Tooltip.Trigger 
                role="tab"
                class="btn btn-sm flex items-center justify-center rounded-xl p-0 transition-all w-8 h-8 min-h-0 border-0 {activeTab === 'tuning' ? 'bg-primary text-primary-content hover:bg-primary' : 'bg-transparent text-base-content/70 hover:bg-base-300/50 hover:text-base-content'}"
                onclick={() => activeTab = 'tuning'}
              >
                <Sliders size={16} />
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content class="z-50 rounded-xl border border-base-content/10 bg-neutral text-neutral-content px-3 py-1.5 text-xs shadow-lg" side="right">
                  System Tuning
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          {/if}
        </li>
      </ul>
    </div>

    <!-- Sidebar Footer -->
    <div class="border-t border-base-content/10 pt-3 flex flex-col gap-2 w-full items-center">
      <div class="flex items-center justify-between w-full {sidebarExpanded ? 'flex-row' : 'flex-col gap-2'}">
        {#if sidebarExpanded}
          <div class="flex flex-col gap-0.5 text-2xs text-base-content/40">
            <div class="flex items-center gap-1.5">
              <span class="inline-block w-1.5 h-1.5 rounded-full {backendConnected ? 'bg-primary' : 'bg-error'}"></span>
              <span>{backendConnected ? 'Connected' : 'Offline'}</span>
            </div>
            <span>v0.9.0-beta</span>
          </div>
        {:else}
          <Tooltip.Root>
            <Tooltip.Trigger class="cursor-default">
              <span class="inline-block w-2.5 h-2.5 rounded-full {backendConnected ? 'bg-primary' : 'bg-error'}"></span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content class="z-50 rounded-xl border border-base-content/10 bg-neutral text-neutral-content px-3 py-1.5 text-xs shadow-lg" side="right">
                {backendConnected ? 'Connected' : 'Offline'}
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        {/if}

        <button 
          class="btn btn-xs btn-ghost btn-circle text-base-content/70 hover:text-base-content"
          onclick={() => settingsOpen = true}
          aria-label="Settings"
        >
          <Settings size={16} />
        </button>
      </div>
    </div>
  </aside>

  <!-- Main Content Spoke (Independent scrolling h-full overflow-y-auto) -->
  <main class="flex-1 h-full overflow-y-auto p-4 md:p-5 max-w-5xl">
    {#if activeTab === 'dashboard'}
      <DashboardTab 
        {health} 
        {ram} 
        {devices} 
        {swaps} 
        {hibernation} 
        {psi} 
        {backendConnected} 
        onConfigureDevice={handleConfigureDevice} 
        onManageHibernation={() => activeTab = 'hibernation'} 
      />
    {:else}
      <div class="flex flex-col gap-4 animate-fade-in">
        {#if activeTab === 'zram'}
          <ZramConfigTab 
            {devices} 
            {showToast} 
            {requestConfirmation} 
          />
        {:else if activeTab === 'hibernation'}
          <HibernationTab 
            {swaps} 
            {hibernation} 
            {showToast} 
            {requestConfirmation} 
          />
        {:else if activeTab === 'tuning'}
          <TuningTab 
            {tuning} 
            {showToast} 
          />
        {/if}
      </div>
    {/if}
  </main>
</div>

<!-- Global Settings Drawer -->
<SettingsDrawer 
  bind:open={settingsOpen} 
  bind:themeMode 
  {availableThemes} 
  {backendConnected} 
  onChangeTheme={(theme) => {
    themeMode = theme;
    localStorage.setItem('theme-mode', theme);
  }} 
/>

<!-- Confirmation Modal -->
<ConfirmationModal 
  bind:open={confirmOpen} 
  title={confirmTitle} 
  desc={confirmDesc} 
  onConfirm={() => {
    if (confirmCallback) confirmCallback();
  }} 
/>

<!-- Toast Notifications -->
{#if toast}
  <div class="toast toast-bottom toast-end z-[100] animate-slide-in">
    <div class="alert {toast.type === 'success' ? 'alert-success' : toast.type === 'error' ? 'alert-error' : 'alert-info'} shadow-lg rounded-xl border border-base-content/10">
      <div class="flex items-center gap-2">
        {#if toast.type === 'error'}
          <ShieldAlert size={16} />
        {/if}
        <span class="text-xs font-semibold">{toast.message}</span>
      </div>
    </div>
  </div>
{/if}
</Tooltip.Provider>