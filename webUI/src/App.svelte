<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { 
    LayoutDashboard, Gauge, Database, Sliders, Info, Loader2, Plus, 
    Settings, CheckCircle2, AlertTriangle, 
    RefreshCw, Trash2, ShieldAlert
  } from 'lucide-svelte';
  import { Tooltip } from 'bits-ui';
  import HealthStrip from './lib/components/HealthStrip.svelte';
  import ZramGaugesList from './lib/components/ZramGaugesList.svelte';
  import ColdTierSwap from './lib/components/ColdTierSwap.svelte';
  import SystemPressure from './lib/components/SystemPressure.svelte';
  import AmbientTuning from './lib/components/AmbientTuning.svelte';
  import SettingsDrawer from './lib/components/SettingsDrawer.svelte';
  import ConfirmationModal from './lib/components/ConfirmationModal.svelte';
  import Select from './lib/components/Select.svelte';
  import { formatBytesToSizeString } from './lib/utils';
  import { initSidecarBridge, sendToPython, onPython } from './lib/bridge';

  // Global UI State
  let activeTab = $state<'dashboard' | 'zram' | 'hibernation' | 'tuning'>('dashboard');
  let backendConnected = $state(false);
  let themeMode = $state('system');
  let settingsOpen = $state(false);

  // System Health
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

  // RAM Info
  let ram = $state({
    total: 0,
    used: 0,
    free: 0,
    shared: 0,
    buff_cache: 0,
    available: 0
  });

  // Telemetry Telemetry
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

  // Cooldown timers to prevent UI flickering on manual tuning changes
  let lastSwappinessChange = 0;
  let lastVfsCachePressureChange = 0;
  let lastCpuGovernorChange = 0;

  // Local state for tunable controls
  let localSwappiness = $state(60);
  let localVfsCachePressure = $state(100);
  let localCpuGovernor = $state('powersave');

  let loadingSwappiness = $state(false);
  let loadingVfsCachePressure = $state(false);
  let loadingCpuGovernor = $state(false);

  // Advanced options toggle for ZRAM Config Spoke
  let showAdvancedOptions = $state<Record<string, boolean>>({});

  // Form states for ZRAM config
  let zramForms = $state<Record<string, {
    algo: string;
    size: string;
    backingDev: string;
    loading: boolean;
  }>>({});

  // New ZRAM device form state
  let newDeviceAlgo = $state('zstd');
  let newDeviceSize = $state('2G');
  let loadingNewDevice = $state(false);

  // Swap manager form state
  let swapPath = $state('/var/lib/swapfile');
  let swapSizeMb = $state(4096);
  let swapPriority = $state(-2);
  let loadingHibernate = $state(false);
  let loadingBoot = $state(false);

  // Power policy settings
  let lidCloseHibernate = $state(false);
  let hibernateDelay = $state(30);

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

  // Helper to initialize/update ZRAM form state from telemetry
  function updateZramForms(devList: any[]) {
    devList.forEach((dev) => {
      const existing = zramForms[dev.name];
      if (!existing) {
        zramForms[dev.name] = {
          algo: dev.algo || 'zstd',
          size: formatBytesToSizeString(dev.totalBytes),
          backingDev: dev.backingDev || 'none',
          loading: false
        };
      } else if (!existing.loading && activeTab !== 'zram') {
        existing.algo = dev.algo || 'zstd';
        existing.size = formatBytesToSizeString(dev.totalBytes);
        existing.backingDev = dev.backingDev || 'none';
      }
    });
  }

  onMount(() => {
    if (typeof window !== 'undefined' && !window.webkit?.messageHandlers?.zmanager) {
      initSidecarBridge(8000);
    }

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

    // Get all available themes from stylesheet
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

    // Listen to Python updates
    onPython('dashboard_update', (data) => {
      backendConnected = true;
      if (data.health) health = data.health;
      if (data.ram) ram = data.ram;
      if (data.devices) {
        devices = data.devices;
        updateZramForms(devices);
      }
      if (data.swaps) swaps = data.swaps;
      if (data.hibernation) hibernation = data.hibernation;
      if (data.psi) psi = data.psi;
      if (data.tuning) {
        tuning = data.tuning;
        const now = Date.now();
        if (!loadingSwappiness && (now - lastSwappinessChange > 2000) && tuning.swappiness !== undefined) {
          localSwappiness = tuning.swappiness;
        }
        if (!loadingVfsCachePressure && (now - lastVfsCachePressureChange > 2000) && tuning.vfs_cache_pressure !== undefined) {
          localVfsCachePressure = tuning.vfs_cache_pressure;
        }
        if (!loadingCpuGovernor && (now - lastCpuGovernorChange > 2000) && tuning.cpu_governor !== undefined) {
          localCpuGovernor = tuning.cpu_governor;
        }
      }
    });

    onPython('connection_status', (connected) => {
      backendConnected = connected;
    });

    return () => {
      if (toastTimeout) clearTimeout(toastTimeout);
    };
  });

  // Apply active theme to document root
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

  // ZRAM Spoke Actions
  async function applyZramConfig(deviceName: string) {
    const form = zramForms[deviceName];
    if (!form) return;
    form.loading = true;
    try {
      const data = await sendToPython('configure_zram', {
        device: deviceName,
        size: form.size,
        algo: form.algo,
        backing_dev: form.backingDev === 'none' ? null : form.backingDev
      });
      if (data.status === 'success') {
        showToast('success', data.message);
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Configuration failed: ${e.message}`);
    } finally {
      form.loading = false;
    }
  }

  async function createZramDevice() {
    loadingNewDevice = true;
    try {
      const data = await sendToPython('create_zram', {
        size: newDeviceSize,
        algo: newDeviceAlgo
      });
      if (data.status === 'success') {
        showToast('success', data.message);
        newDeviceSize = '2G';
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Creation failed: ${e.message}`);
    } finally {
      loadingNewDevice = false;
    }
  }

  function resetZramDevice(deviceName: string) {
    requestConfirmation(
      `Reset ZRAM Device ${deviceName}?`,
      `This will run 'systemctl restart systemd-zram-setup@${deviceName}.service'. Any unwritten compressed data in this ZRAM device will be lost.`,
      async () => {
        if (zramForms[deviceName]) zramForms[deviceName].loading = true;
        try {
          const data = await sendToPython('reset_zram', { device: deviceName });
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Reset failed: ${e.message}`);
        } finally {
          if (zramForms[deviceName]) zramForms[deviceName].loading = false;
        }
      }
    );
  }

  // Remove ZRAM Device
  function removeZramDevice(deviceName: string) {
    requestConfirmation(
      `Remove ZRAM Device ${deviceName}?`,
      `This will remove the configuration for ${deviceName} from /etc/systemd/zram-generator.conf and stop its service.`,
      async () => {
        if (zramForms[deviceName]) zramForms[deviceName].loading = true;
        try {
          const data = await sendToPython('remove_zram', { device: deviceName });
          if (data.status === 'success') {
            showToast('success', data.message);
            delete zramForms[deviceName];
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Removal failed: ${e.message}`);
        } finally {
          if (zramForms[deviceName]) zramForms[deviceName].loading = false;
        }
      }
    );
  }

  // Hibernation Actions
  function setupHibernation() {
    requestConfirmation(
      'Setup Hibernation Swap?',
      `This will provision a swap space at ${swapPath} of size ${swapSizeMb}MB, persist it in systemd, configure kernel resume parameters, and update initramfs. This requires root privileges and will take a moment.`,
      async () => {
        loadingHibernate = true;
        try {
          const data = await sendToPython('setup_hibernation', {
            swap_path: swapPath,
            size_mb: swapSizeMb,
            priority: swapPriority
          });
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Setup failed: ${e.message}`);
        } finally {
          loadingHibernate = false;
        }
      }
    );
  }

  function regenerateBoot() {
    requestConfirmation(
      'Regenerate Bootloader & Initramfs?',
      'This will run update-grub and update-initramfs to apply the current resume parameters. This can take up to a minute.',
      async () => {
        loadingBoot = true;
        try {
          const data = await sendToPython('update_boot');
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Regeneration failed: ${e.message}`);
        } finally {
          loadingBoot = false;
        }
      }
    );
  }

  // Power policy save mock
  function savePowerPolicy() {
    showToast('success', 'Power policy saved successfully.');
  }

  function handleConfigureDevice(name: string) {
    activeTab = 'zram';
  }

  // Apply manual tuning change
  async function applyTuningChange(type: 'swappiness' | 'vfs_cache_pressure' | 'cpu_governor', value: any) {
    if (type === 'swappiness') {
      loadingSwappiness = true;
      lastSwappinessChange = Date.now();
    }
    if (type === 'vfs_cache_pressure') {
      loadingVfsCachePressure = true;
      lastVfsCachePressureChange = Date.now();
    }
    if (type === 'cpu_governor') {
      loadingCpuGovernor = true;
      lastCpuGovernorChange = Date.now();
    }

    try {
      const data = await sendToPython('apply_tuning', { type, value });
      if (data.status === 'success') {
        showToast('success', data.message);
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Tuning change failed: ${e.message}`);
    } finally {
      if (type === 'swappiness') loadingSwappiness = false;
      if (type === 'vfs_cache_pressure') loadingVfsCachePressure = false;
      if (type === 'cpu_governor') loadingCpuGovernor = false;
    }
  }

  // Health status dot class for sidebar
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
<div class="flex flex-row min-h-screen bg-base-100 text-base-content relative z-10">
  
  <!-- Sidebar Navigation (Narrower: w-44, compact spacing) -->
  <aside class="w-44 bg-base-200 border-r border-base-content/10 p-3 flex flex-col justify-between shrink-0 select-none">
    <div class="flex flex-col gap-4">
      <!-- Sidebar Header -->
      <div class="flex items-center gap-2.5 px-1 py-2">
        <span class="w-3 h-3 rounded-full {healthDotClass} transition-colors duration-500 shadow-sm"></span>
        <h1 class="text-lg font-bold tracking-tight font-sans">Z-Manager</h1>
      </div>
      
      <!-- Navigation Menu (Compact px-3 py-2, gap-1) -->
      <ul role="tablist" class="menu p-0 gap-1 text-sm">
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'dashboard' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'dashboard'}
          >
            <LayoutDashboard size={16} /> Dashboard
          </button>
        </li>
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'zram' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'zram'}
          >
            <Gauge size={16} /> ZRAM Config
          </button>
        </li>
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'hibernation' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'hibernation'}
          >
            <Database size={16} /> Hibernation
          </button>
        </li>
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2 px-3 py-2 rounded-xl transition-all {activeTab === 'tuning' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'tuning'}
          >
            <Sliders size={16} /> Tuning
          </button>
        </li>
      </ul>
    </div>

    <!-- Sidebar Footer -->
    <div class="border-t border-base-content/10 pt-3 flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <div class="flex flex-col gap-0.5 text-2xs text-base-content/40">
          <div class="flex items-center gap-1.5">
            <span class="inline-block w-1.5 h-1.5 rounded-full {backendConnected ? 'bg-primary' : 'bg-error'}"></span>
            <span>{backendConnected ? 'Connected' : 'Offline'}</span>
          </div>
          <span>v0.9.0-beta</span>
        </div>
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

  <!-- Main Content Spoke (Tighter padding: p-4 md:p-5, gap-4) -->
  <main class="flex-1 p-4 md:p-5 overflow-y-auto max-w-5xl">
    {#if activeTab === 'dashboard'}
      <!-- DASHBOARD (THE HUB) -->
      <div class="flex flex-col gap-4 animate-fade-in">
        
        <!-- Zone A: Health Strip -->
        <HealthStrip 
          {health} 
          {ram} 
          {devices} 
          {hibernation} 
          {backendConnected} 
        />

        <!-- Zone B: ZRAM Live Telemetry (Compact p-4, gap-4) -->
        <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-md font-bold">ZRAM Live Telemetry</h2>
              <p class="text-xs text-base-content/60">Hot Tier · Fast volatile RAM compression</p>
            </div>
            <button 
              class="btn btn-xs btn-ghost font-semibold"
              onclick={() => activeTab = 'zram'}
            >
              Configure
            </button>
          </div>

          {#if devices.length > 0}
            <ZramGaugesList 
              {devices} 
              onConfigureDevice={handleConfigureDevice} 
            />
          {:else}
            <div class="py-8 flex flex-col items-center justify-center text-center w-full">
              <Loader2 class="animate-spin text-primary mb-2" size={20} />
              <p class="text-xs text-base-content/60">Waiting for ZRAM telemetry...</p>
            </div>
          {/if}
        </div>

        <!-- Row 3: Cold Tier & System Pressure (Tighter gap-4) -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          
          <!-- Zone C: Cold Tier & Swap Summary (Compact p-4, gap-4) -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Database class="text-secondary" size={20} />
                <div>
                  <h2 class="text-md font-bold">Cold Tier & Swap</h2>
                  <p class="text-xs text-base-content/60">Persistent Storage · Swap files & partitions</p>
                </div>
              </div>
              <button 
                class="btn btn-xs btn-ghost font-semibold"
                onclick={() => activeTab = 'hibernation'}
              >
                Manage
              </button>
            </div>

            <div class="flex flex-col gap-3">
              <!-- Readiness Badge -->
              <div class="flex items-center gap-3 bg-base-200/30 border border-base-content/5 p-3 rounded-xl">
                <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50">Readiness:</span>
                
                <Tooltip.Root>
                  <Tooltip.Trigger class="badge badge-sm {hibernation.ready ? 'badge-primary' : 'badge-warning animate-pulse'} font-semibold gap-1 cursor-help shrink-0">
                    {#if hibernation.ready}
                      <CheckCircle2 size={12} /> Ready
                    {:else}
                      <AlertTriangle size={12} /> Config Needed
                    {/if}
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                      {hibernation.message}
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </div>

              <!-- Swap Tiers list -->
              <div class="flex flex-col gap-1.5 bg-base-200/30 border border-base-content/5 p-3 rounded-xl">
                <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-0.5">Active Swap Tiers</span>
                {#each swaps as swap}
                  <div class="flex items-center justify-between text-xs font-mono">
                    <span class="font-bold text-base-content/80">{swap.name}</span>
                    <span class="text-base-content/60">{swap.used} / {swap.size} (Pri {swap.priority})</span>
                  </div>
                {:else}
                  <span class="text-xs text-base-content/40 italic">No disk swap active</span>
                {/each}
              </div>
            </div>
          </div>

          <!-- Zone D: System Pressure -->
          <SystemPressure {psi} />

        </div>
      </div>
    {:else}
      <!-- SPOKES (CONFIGURATION VIEWS) -->
      <div class="flex flex-col gap-4 animate-fade-in">
        
        {#if activeTab === 'zram'}
          <!-- ZRAM CONFIGURATION SPOKE (Compact p-4, gap-4) -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-md font-bold">ZRAM Configuration</h2>
                <p class="text-xs text-base-content/60">Create, modify, or remove ZRAM devices</p>
              </div>
              <button 
                class="btn btn-xs btn-ghost font-semibold"
                onclick={() => activeTab = 'dashboard'}
              >
                Back to Dashboard
              </button>
            </div>

            <!-- Two column layout for creation form and active devices list -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
              <!-- Active ZRAM Devices list (Left 2 columns, grid of cards) -->
              <div class="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                {#each devices as dev}
                  {@const form = zramForms[dev.name]}
                  {#if form}
                    <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-4 flex flex-col justify-between gap-3.5 relative min-h-[220px]">
                      {#if form.loading}
                        <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                          <Loader2 class="animate-spin text-primary" size={20} />
                        </div>
                      {/if}

                      <div class="flex flex-col gap-3.5">
                        <div class="flex items-center justify-between border-b border-base-content/5 pb-2">
                          <span class="text-sm font-bold font-mono text-primary">{dev.name}</span>
                          <div class="flex gap-1.5">
                            <button 
                              class="btn btn-2xs btn-error btn-soft"
                              onclick={() => removeZramDevice(dev.name)}
                            >
                              Remove
                            </button>
                            <button 
                              class="btn btn-2xs btn-neutral btn-soft"
                              onclick={() => resetZramDevice(dev.name)}
                            >
                              Reset
                            </button>
                          </div>
                        </div>

                        <div class="grid grid-cols-2 gap-2.5">
                          <label class="form-control">
                            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Algorithm</span>
                            <Select 
                              bind:value={form.algo}
                              items={[
                                { value: 'zstd', label: 'zstd (Recommended)' },
                                { value: 'lz4', label: 'lz4 (Fastest)' },
                                { value: 'lzo', label: 'lzo' },
                                { value: 'deflate', label: 'deflate' }
                              ]}
                            />
                          </label>

                          <label class="form-control">
                            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Size</span>
                            <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. 2G" bind:value={form.size} />
                          </label>
                        </div>

                        <!-- Progressive Disclosure Fold for Advanced Options -->
                        <div class="flex flex-col gap-2">
                          <button 
                            class="btn btn-2xs btn-ghost justify-start gap-1 p-0 hover:bg-transparent font-bold text-3xs uppercase tracking-wider text-base-content/50"
                            onclick={() => showAdvancedOptions[dev.name] = !showAdvancedOptions[dev.name]}
                          >
                            <span>{showAdvancedOptions[dev.name] ? '▼ hide advanced' : '▶ show advanced'}</span>
                          </button>
                          
                          {#if showAdvancedOptions[dev.name]}
                            <div class="flex flex-col gap-1 animate-fade-in bg-base-300/30 p-2.5 rounded-xl border border-base-content/5">
                              <label class="form-control w-full">
                                <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Writeback Backing Device</span>
                                <input type="text" class="input input-xs input-bordered w-full font-mono" placeholder="e.g. /dev/nvme0n1p3 or none" bind:value={form.backingDev} />
                              </label>
                            </div>
                          {/if}
                        </div>
                      </div>

                      <button 
                        class="btn btn-xs btn-primary w-full mt-2 font-bold"
                        onclick={() => applyZramConfig(dev.name)}
                      >
                        Apply & Restart
                      </button>
                    </div>
                  {/if}
                {:else}
                  <div class="md:col-span-2 py-12 flex flex-col items-center justify-center text-center w-full bg-base-200/20 border border-base-content/5 rounded-2xl">
                    <Info size={28} class="mb-2 opacity-50 text-base-content/40" />
                    <p class="text-xs text-base-content/60 font-semibold">No active ZRAM devices configured.</p>
                  </div>
                {/each}
              </div>

              <!-- Create New Device Card (Right column) -->
              <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-4 flex flex-col gap-3.5 relative">
                {#if loadingNewDevice}
                  <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                    <Loader2 class="animate-spin text-primary" size={20} />
                  </div>
                {/if}

                <h3 class="text-sm font-bold text-base-content/80 flex items-center gap-2 border-b border-base-content/5 pb-2">
                  <Plus size={16} /> Create ZRAM Device
                </h3>

                <div class="grid grid-cols-1 gap-3">
                  <label class="form-control">
                    <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Algorithm</span>
                    <Select 
                      bind:value={newDeviceAlgo}
                      items={[
                        { value: 'zstd', label: 'zstd (Recommended)' },
                        { value: 'lz4', label: 'lz4 (Fastest)' },
                        { value: 'lzo', label: 'lzo' },
                        { value: 'deflate', label: 'deflate' }
                      ]}
                    />
                  </label>

                  <label class="form-control">
                    <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Size</span>
                    <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. 2G" bind:value={newDeviceSize} />
                  </label>

                  <button 
                    class="btn btn-sm btn-primary w-full mt-2 font-bold"
                    onclick={createZramDevice}
                  >
                    Create Device
                  </button>
                </div>
              </div>
            </div>
          </div>
        {:else if activeTab === 'hibernation'}
          <!-- HIBERNATION CONFIGURATION SPOKE (Compact p-4, gap-4) -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-md font-bold">Hibernation & Boot Config</h2>
                <p class="text-xs text-base-content/60">Configure swap files, system resume parameters, and power settings</p>
              </div>
              <button 
                class="btn btn-xs btn-ghost font-semibold"
                onclick={() => activeTab = 'dashboard'}
              >
                Back to Dashboard
              </button>
            </div>

            <ColdTierSwap 
              {swaps} 
              {hibernation} 
              bind:swapPath 
              bind:swapSizeMb 
              bind:swapPriority 
              {loadingHibernate} 
              {loadingBoot} 
              bind:lidCloseHibernate 
              bind:hibernateDelay 
              onSetupHibernation={setupHibernation} 
              onRegenerateBoot={regenerateBoot} 
              onSavePowerPolicy={savePowerPolicy} 
            />
          </div>
        {:else if activeTab === 'tuning'}
          <!-- SYSTEM TUNING SPOKE (Compact p-4, gap-4) -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-md font-bold">Kernel & CPU Tuning</h2>
                <p class="text-xs text-base-content/60">Optimize virtual memory swappiness, cache reclaim pressure, and CPU scheduler governor</p>
              </div>
              <button 
                class="btn btn-xs btn-ghost font-semibold"
                onclick={() => activeTab = 'dashboard'}
              >
                Back to Dashboard
              </button>
            </div>

            <AmbientTuning 
              {tuning}
              bind:localSwappiness
              bind:localVfsCachePressure
              bind:localCpuGovernor
              {loadingSwappiness}
              {loadingVfsCachePressure}
              {loadingCpuGovernor}
              onApplyTuningChange={applyTuningChange}
            />
          </div>
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