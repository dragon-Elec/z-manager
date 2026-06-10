<script lang="ts">
  import { onMount } from 'svelte';
  import { sendToPython, onPython, initSidecarBridge } from '$lib/bridge';
  import { Tooltip, DropdownMenu } from 'bits-ui';
  import { 
    Settings, Database, AlertTriangle, Sliders, Cpu, RefreshCw, Trash2, 
    Loader2, Plus, CheckCircle2, ChevronDown, ChevronUp, Activity, Info,
    Gauge, LayoutDashboard, ShieldAlert
  } from 'lucide-svelte';

  // Import modular components
  import HealthStrip from '$lib/components/HealthStrip.svelte';
  import ZramGaugesList from '$lib/components/ZramGaugesList.svelte';
  import ColdTierSwap from '$lib/components/ColdTierSwap.svelte';
  import SystemPressure from '$lib/components/SystemPressure.svelte';
  import AmbientTuning from '$lib/components/AmbientTuning.svelte';
  import SettingsDrawer from '$lib/components/SettingsDrawer.svelte';
  import ConfirmationModal from '$lib/components/ConfirmationModal.svelte';

  // Telemetry state
  let devices = $state<any[]>([]);
  let ram = $state({ total: 1, used: 0 });
  let swaps = $state<any[]>([]);
  let psi = $state<any>({
    cpu: { some: 0, full: 0 },
    memory: { some: 0, full: 0 },
    io: { some: 0, full: 0 }
  });
  let hibernation = $state<any>({
    ready: false,
    secure_boot: 'disabled',
    swap_total: 0,
    ram_total: 1,
    recommended_swap_bytes: 0,
    message: 'Probing hibernation...'
  });
  let tuning = $state<any>({
    swappiness: 60,
    vfs_cache_pressure: 100,
    cpu_governor: 'powersave',
    available_governors: ['powersave', 'performance', 'schedutil']
  });
  let health = $state<any>({
    zramctl_available: true,
    systemd_available: true,
    sysfs_root_accessible: true,
    zswap: { available: false, enabled: false, detail: '' },
    journal_available: true,
    kernel_version: '',
    devices_summary: '',
    notes: []
  });

  // UI state
  let activeTab = $state<'dashboard' | 'zram' | 'hibernation'>('dashboard');
  let settingsOpen = $state(false);
  let lastUpdate = $state<Date | null>(null);
  let backendConnected = $derived(lastUpdate !== null && (Date.now() - lastUpdate.getTime() < 3000));

  // Theme state
  let themeMode = $state<string>('system');
  let systemIsDark = $state(false);
  const availableThemes = [
    'light', 'dark', 'cupcake', 'bumblebee', 'emerald', 'corporate',
    'synthwave', 'retro', 'cyberpunk', 'valentine', 'halloween', 'garden',
    'forest', 'aqua', 'lofi', 'pastel', 'fantasy', 'wireframe', 'black',
    'luxury', 'dracula', 'cmyk', 'autumn', 'business', 'acid', 'lemonade',
    'night', 'coffee', 'winter', 'dim', 'nord', 'sunset', 'caramellatte',
    'abyss', 'silk'
  ];

  // Optimistic UI local state for tunables
  let localSwappiness = $state(60);
  let localVfsCachePressure = $state(100);
  let localCpuGovernor = $state('powersave');

  let loadingSwappiness = $state(false);
  let loadingVfsCachePressure = $state(false);
  let loadingCpuGovernor = $state(false);

  // ZRAM Device form configuration state
  let zramForms = $state<Record<string, { algo: string; size: string; backingDev: string; loading: boolean }>>({});
  let newDeviceAlgo = $state('zstd');
  let newDeviceSize = $state('2G');
  let newDeviceBacking = $state('none');
  let loadingNewDevice = $state(false);

  // Hibernation setup form state
  let swapPath = $state('/swapfile');
  let swapSizeMb = $state(16384);
  let swapPriority = $state(0);
  let loadingHibernate = $state(false);
  let loadingBoot = $state(false);

  // Power policy mock state (persisted locally)
  let lidCloseHibernate = $state(true);
  let hibernateDelay = $state(30);

  // Confirmation dialog state
  let confirmOpen = $state(false);
  let confirmTitle = $state('');
  let confirmDesc = $state('');
  let confirmAction = $state<(() => void) | null>(null);

  // Toast notifications state
  let toast = $state<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  let toastTimeout: any = null;

  function showToast(type: 'success' | 'error' | 'info', message: string) {
    if (toastTimeout) clearTimeout(toastTimeout);
    toast = { type, message };
    toastTimeout = setTimeout(() => {
      toast = null;
    }, 4000);
  }

  function requestConfirmation(title: string, desc: string, action: () => void) {
    confirmTitle = title;
    confirmDesc = desc;
    confirmAction = () => {
      action();
      confirmOpen = false;
    };
    confirmOpen = true;
  }

  // Format bytes to human readable
  function formatSize(size: number) {
    let s = size;
    for (const unit of ['B', 'KiB', 'MiB', 'GiB', 'TiB']) {
      if (Math.abs(s) < 1024.0) {
        return `${s.toFixed(1)} ${unit}`;
      }
      s /= 1024.0;
    }
    return `${s.toFixed(1)} PiB`;
  }

  // Format bytes to clean size string (e.g. 2G)
  function formatBytesToSizeString(bytes: number) {
    if (bytes <= 0) return '1G';
    const gb = bytes / (1024 ** 3);
    if (gb >= 1) return `${Math.round(gb)}G`;
    const mb = bytes / (1024 ** 2);
    return `${Math.round(mb)}M`;
  }

  let activeTheme = $derived.by(() => {
    if (themeMode === 'system') {
      return systemIsDark ? 'forest' : 'nord';
    }
    if (themeMode === 'dark') {
      return 'forest';
    }
    if (themeMode === 'light') {
      return 'nord';
    }
    return themeMode;
  });

  // Theme application
  $effect(() => {
    if (typeof document !== 'undefined') {
      console.log("[Theme] Applying theme:", activeTheme);
      document.documentElement.setAttribute('data-theme', activeTheme);
    }
  });

  // Helper to initialize/update ZRAM form state from telemetry
  function updateZramForms(devList: any[]) {
    devList.forEach((dev) => {
      if (!zramForms[dev.name]) {
        zramForms[dev.name] = {
          algo: dev.algo || 'zstd',
          size: formatBytesToSizeString(dev.totalBytes),
          backingDev: dev.backingDev || 'none',
          loading: false
        };
      }
    });
  }

  onMount(() => {
    if (typeof window !== 'undefined' && !window.webkit?.messageHandlers?.zmanager) {
      initSidecarBridge(8000);
    }

    // Prevent pinch-to-zoom gestures
    document.addEventListener('touchmove', (event) => {
      if (event.touches.length > 1) {
        event.preventDefault();
      }
    }, { passive: false });

    // Prevent zoom via Ctrl + Mouse Wheel (Desktop)
    document.addEventListener('wheel', (event) => {
      if (event.ctrlKey) {
        event.preventDefault();
      }
    }, { passive: false });

    // Read stored theme
    const stored = localStorage.getItem('zman-theme');
    if (stored) {
      themeMode = stored;
    }
    
    // Check system preference
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    systemIsDark = media.matches;
    const listener = (e: MediaQueryListEvent) => {
      systemIsDark = e.matches;
    };
    media.addEventListener('change', listener);
    
    // Listen for updates from Python
    onPython('dashboard_update', (data: any) => {
      lastUpdate = new Date();
      if (data.devices) {
        devices = data.devices;
        updateZramForms(devices);
      }
      if (data.ram) ram = data.ram;
      if (data.swaps) swaps = data.swaps;
      if (data.psi) psi = data.psi;
      if (data.hibernation) {
        hibernation = data.hibernation;
        if (hibernation.recommended_swap_bytes > 0 && swapSizeMb === 16384) {
          swapSizeMb = Math.ceil(hibernation.recommended_swap_bytes / (1024 ** 2));
        }
      }
      if (data.tuning) {
        tuning = data.tuning;
        if (!loadingSwappiness && tuning.swappiness !== undefined) {
          localSwappiness = tuning.swappiness;
        }
        if (!loadingVfsCachePressure && tuning.vfs_cache_pressure !== undefined) {
          localVfsCachePressure = tuning.vfs_cache_pressure;
        }
        if (!loadingCpuGovernor && tuning.cpu_governor !== undefined) {
          localCpuGovernor = tuning.cpu_governor;
        }
      }
      if (data.health) {
        health = data.health;
      }
    });

    // Request initial data
    sendToPython('get_dashboard_data');

    return () => media.removeEventListener('change', listener);
  });

  function changeTheme(mode: string) {
    themeMode = mode;
    localStorage.setItem('zman-theme', mode);
  }

  // Tuning Apply
  async function applyTuningChange(type: 'swappiness' | 'vfs_cache_pressure' | 'cpu_governor', value: any) {
    if (type === 'swappiness') loadingSwappiness = true;
    if (type === 'vfs_cache_pressure') loadingVfsCachePressure = true;
    if (type === 'cpu_governor') loadingCpuGovernor = true;

    try {
      const data = await sendToPython('apply_tuning', {
        swappiness: type === 'swappiness' ? value : undefined,
        vfs_cache_pressure: type === 'vfs_cache_pressure' ? value : undefined,
        cpu_governor: type === 'cpu_governor' ? value : undefined,
      });

      if (data.status === 'success') {
        showToast('success', data.message || 'Tuning applied successfully.');
      } else {
        showToast('error', data.message || 'Failed to apply tuning.');
        rollbackTuning(type);
      }
    } catch (e: any) {
      showToast('error', `Error: ${e.message}`);
      rollbackTuning(type);
    } finally {
      if (type === 'swappiness') loadingSwappiness = false;
      if (type === 'vfs_cache_pressure') loadingVfsCachePressure = false;
      if (type === 'cpu_governor') loadingCpuGovernor = false;
    }
  }

  function rollbackTuning(type: 'swappiness' | 'vfs_cache_pressure' | 'cpu_governor') {
    if (type === 'swappiness') localSwappiness = tuning.swappiness;
    if (type === 'vfs_cache_pressure') localVfsCachePressure = tuning.vfs_cache_pressure;
    if (type === 'cpu_governor') localCpuGovernor = tuning.cpu_governor;
  }

  // ZRAM Actions
  async function applyZramConfig(deviceName: string) {
    const form = zramForms[deviceName];
    if (!form) return;
    form.loading = true;

    try {
      const data = await sendToPython('configure_zram', {
        device: deviceName,
        algo: form.algo,
        size: form.size,
        backingDev: form.backingDev === 'none' ? '' : form.backingDev
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
    // Find next available device name (e.g. zram0, zram1)
    let nextIndex = 0;
    while (devices.some(d => d.name === `zram${nextIndex}`)) {
      nextIndex++;
    }
    const deviceName = `zram${nextIndex}`;
    loadingNewDevice = true;

    try {
      const data = await sendToPython('configure_zram', {
        device: deviceName,
        algo: newDeviceAlgo,
        size: newDeviceSize,
        backingDev: newDeviceBacking === 'none' ? '' : newDeviceBacking
      });
      if (data.status === 'success') {
        showToast('success', data.message);
        activeTab = 'dashboard';
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
            // Remove from local form state
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
  
  <!-- Sidebar Navigation -->
  <aside class="w-64 bg-base-200 border-r border-base-content/10 p-4 flex flex-col justify-between shrink-0">
    <div class="flex flex-col gap-6">
      <!-- Sidebar Header -->
      <div class="flex items-center gap-3 px-2 py-3">
        <span class="w-3.5 h-3.5 rounded-full {healthDotClass} transition-colors duration-500 shadow-sm"></span>
        <h1 class="text-xl font-bold tracking-tight font-sans">Z-Manager</h1>
      </div>
      
      <!-- Navigation Menu -->
      <ul role="tablist" class="menu p-0 gap-1.5">
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2.5 px-4 py-2.5 rounded-xl transition-all {activeTab === 'dashboard' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'dashboard'}
          >
            <LayoutDashboard size={18} /> Dashboard
          </button>
        </li>
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2.5 px-4 py-2.5 rounded-xl transition-all {activeTab === 'zram' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'zram'}
          >
            <Gauge size={18} /> ZRAM Config
          </button>
        </li>
        <li>
          <button 
            role="tab"
            class="font-semibold flex items-center gap-2.5 px-4 py-2.5 rounded-xl transition-all {activeTab === 'hibernation' ? 'active bg-primary text-primary-content' : 'text-base-content/70 hover:text-base-content hover:bg-base-300/50'}" 
            onclick={() => activeTab = 'hibernation'}
          >
            <Database size={18} /> Hibernation
          </button>
        </li>
      </ul>
    </div>

    <!-- Sidebar Footer -->
    <div class="border-t border-base-content/10 pt-4 flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <div class="flex flex-col gap-1 text-xs text-base-content/40">
          <div class="flex items-center gap-2">
            <span class="inline-block w-2 h-2 rounded-full {backendConnected ? 'bg-primary' : 'bg-error'}"></span>
            <span>{backendConnected ? 'Connected' : 'Connecting...'}</span>
          </div>
          <span>v0.9.0-beta</span>
        </div>
        <button 
          class="btn btn-sm btn-ghost btn-circle text-base-content/70 hover:text-base-content"
          onclick={() => settingsOpen = true}
          aria-label="Settings"
        >
          <Settings size={18} />
        </button>
      </div>
    </div>
  </aside>

  <!-- Main Content Spoke -->
  <main class="flex-1 p-6 md:p-8 overflow-y-auto max-w-5xl">
    {#if activeTab === 'dashboard'}
      <!-- DASHBOARD (THE HUB) -->
      <div class="flex flex-col gap-6 animate-fade-in">
        
        <!-- Zone A: Health Strip -->
        <HealthStrip 
          {health} 
          {ram} 
          {devices} 
          {hibernation} 
          {backendConnected} 
        />

        <!-- Zone B: ZRAM Live Telemetry -->
        <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-bold">ZRAM Live Telemetry</h2>
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
            <div class="py-12 flex flex-col items-center justify-center text-center w-full">
              <Loader2 class="animate-spin text-primary mb-2" size={24} />
              <p class="text-sm text-base-content/60">Waiting for ZRAM telemetry...</p>
            </div>
          {/if}
        </div>

        <!-- Row 3: Cold Tier & System Pressure -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          
          <!-- Zone C: Cold Tier & Swap Summary -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <Database class="text-secondary" size={22} />
                <div>
                  <h2 class="text-lg font-bold">Cold Tier & Swap</h2>
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

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Readiness Badge -->
              <div class="flex items-center gap-3 bg-base-200/30 border border-base-content/5 p-4 rounded-2xl">
                <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50">Readiness:</span>
                
                <Tooltip.Root>
                  <Tooltip.Trigger class="badge badge-lg {hibernation.ready ? 'badge-primary' : 'badge-warning animate-pulse'} font-semibold gap-1.5 cursor-help">
                    {#if hibernation.ready}
                      <CheckCircle2 size={14} /> Ready
                    {:else}
                      <AlertTriangle size={14} /> Config Needed
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
              <div class="flex flex-col gap-1.5 bg-base-200/30 border border-base-content/5 p-4 rounded-2xl">
                <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-1">Active Swap Tiers</span>
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

        <!-- Zone E: Ambient Tuning -->
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
    {:else}
      <!-- SPOKES (CONFIGURATION VIEWS) -->
      <div class="flex flex-col gap-6 animate-fade-in">
        
        {#if activeTab === 'zram'}
          <!-- ZRAM CONFIGURATION SPOKE -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-bold">ZRAM Configuration</h2>
                <p class="text-xs text-base-content/60">Create, modify, or remove ZRAM devices</p>
              </div>
              <button 
                class="btn btn-xs btn-ghost font-semibold"
                onclick={() => activeTab = 'dashboard'}
              >
                Back to Dashboard
              </button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              <!-- Device List & Forms -->
              <div class="lg:col-span-2 flex flex-col gap-6">
                {#each devices as dev}
                  {@const form = zramForms[dev.name]}
                  {#if form}
                    <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-5 flex flex-col gap-4 relative">
                      {#if form.loading}
                        <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                          <Loader2 class="animate-spin text-primary" size={24} />
                        </div>
                      {/if}

                      <div class="flex items-center justify-between">
                        <span class="text-md font-bold font-mono">{dev.name}</span>
                        <div class="flex gap-2">
                          <button 
                            class="btn btn-xs btn-error btn-soft"
                            onclick={() => removeZramDevice(dev.name)}
                          >
                            <Trash2 size={13} /> Remove
                          </button>
                          <button 
                            class="btn btn-xs btn-neutral btn-soft"
                            onclick={() => resetZramDevice(dev.name)}
                          >
                            <RefreshCw size={13} /> Reset
                          </button>
                        </div>
                      </div>

                      <div class="grid grid-cols-2 gap-3">
                        <label class="form-control">
                          <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Algorithm</span></div>
                          <DropdownMenu.Root>
                            <DropdownMenu.Trigger class="btn btn-sm btn-outline justify-between w-full font-medium">
                              <span>{form.algo}</span>
                              <ChevronDown size={14} class="opacity-60 shrink-0" />
                            </DropdownMenu.Trigger>
                            <DropdownMenu.Portal>
                              <DropdownMenu.Content class="z-50 min-w-[12rem] rounded-xl border border-base-content/10 bg-base-200 p-1 shadow-lg flex flex-col gap-0.5">
                                {#each ['zstd', 'lz4', 'lzo', 'deflate'] as algo}
                                  <DropdownMenu.Item 
                                    class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium {form.algo === algo ? 'bg-primary text-primary-content' : ''}"
                                    onclick={() => form.algo = algo}
                                  >
                                    {algo === 'zstd' ? 'zstd (Recommended)' : algo === 'lz4' ? 'lz4 (Fastest)' : algo}
                                  </DropdownMenu.Item>
                                {/each}
                              </DropdownMenu.Content>
                            </DropdownMenu.Portal>
                          </DropdownMenu.Root>
                        </label>

                        <label class="form-control">
                          <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Size</span></div>
                          <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. 2G or ram/2" bind:value={form.size} />
                        </label>
                      </div>

                      <!-- Advanced Options (Writeback) -->
                      <div class="collapse collapse-arrow bg-base-300/20 border border-base-content/5 rounded-xl">
                        <input type="checkbox" /> 
                        <div class="collapse-title text-xs font-semibold text-base-content/60 py-2 min-h-0">
                          Advanced Options (Writeback)
                        </div>
                        <div class="collapse-content py-2">
                          <label class="form-control">
                            <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Writeback (Backing Device)</span></div>
                            <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. /dev/nvme0n1p3 or none" bind:value={form.backingDev} />
                          </label>
                        </div>
                      </div>

                      <button 
                        class="btn btn-sm btn-primary w-full mt-2"
                        onclick={() => applyZramConfig(dev.name)}
                      >
                        Apply & Restart Service
                      </button>
                    </div>
                  {/if}
                {:else}
                  <div class="py-12 flex flex-col items-center justify-center text-center w-full bg-base-200/20 border border-base-content/5 rounded-2xl">
                    <Info size={32} class="mb-2 opacity-50" />
                    <p class="text-sm text-base-content/60">No active ZRAM devices configured.</p>
                  </div>
                {/each}
              </div>

              <!-- Create New Device Card -->
              <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-5 flex flex-col gap-4 relative">
                {#if loadingNewDevice}
                  <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                    <Loader2 class="animate-spin text-primary" size={24} />
                  </div>
                {/if}

                <h3 class="text-md font-semibold text-base-content/80 flex items-center gap-2">
                  <Plus size={18} /> Create ZRAM Device
                </h3>

                <div class="grid grid-cols-1 gap-3">
                  <label class="form-control">
                    <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Algorithm</span></div>
                    <DropdownMenu.Root>
                      <DropdownMenu.Trigger class="btn btn-sm btn-outline justify-between w-full font-medium">
                        <span>{newDeviceAlgo}</span>
                        <ChevronDown size={14} class="opacity-60 shrink-0" />
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Portal>
                        <DropdownMenu.Content class="z-50 min-w-[12rem] rounded-xl border border-base-content/10 bg-base-200 p-1 shadow-lg flex flex-col gap-0.5">
                          {#each ['zstd', 'lz4', 'lzo', 'deflate'] as algo}
                            <DropdownMenu.Item 
                              class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium {newDeviceAlgo === algo ? 'bg-primary text-primary-content' : ''}"
                              onclick={() => newDeviceAlgo = algo}
                            >
                              {algo === 'zstd' ? 'zstd (Recommended)' : algo === 'lz4' ? 'lz4 (Fastest)' : algo}
                            </DropdownMenu.Item>
                          {/each}
                        </DropdownMenu.Content>
                      </DropdownMenu.Portal>
                    </DropdownMenu.Root>
                  </label>

                  <label class="form-control">
                    <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Size</span></div>
                    <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. 2G or ram/2" bind:value={newDeviceSize} />
                  </label>

                  <label class="form-control">
                    <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Writeback (Backing Device)</span></div>
                    <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. /dev/nvme0n1p3 or none" bind:value={newDeviceBacking} />
                  </label>
                </div>

                <button 
                  class="btn btn-sm btn-primary w-full mt-2"
                  onclick={createZramDevice}
                >
                  Create Device
                </button>
              </div>
            </div>
          </div>
        {:else if activeTab === 'hibernation'}
          <!-- HIBERNATION CONFIGURATION SPOKE -->
          <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-bold">Hibernation & Cold Tier</h2>
                <p class="text-xs text-base-content/60">Configure persistent swap storage and bootloader settings</p>
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
        {/if}

      </div>
    {/if}
  </main>

</div>
</Tooltip.Provider>

<!-- Settings Drawer -->
<SettingsDrawer 
  bind:open={settingsOpen}
  bind:themeMode
  {availableThemes}
  {backendConnected}
  onChangeTheme={changeTheme}
/>

<!-- Confirmation Dialog -->
<ConfirmationModal 
  bind:open={confirmOpen}
  title={confirmTitle}
  desc={confirmDesc}
  onConfirm={() => confirmAction?.()}
/>

<!-- Toast Notifications -->
{#if toast}
  <div class="fixed bottom-4 right-4 z-50 animate-slide-in">
    <div class="alert shadow-lg border border-base-content/10 bg-base-100 flex gap-3 p-4">
      {#if toast.type === 'success'}
        <CheckCircle2 class="text-primary shrink-0" size={20} />
      {:else if toast.type === 'error'}
        <XCircle class="text-error shrink-0" size={20} />
      {:else}
        <Info class="text-info shrink-0" size={20} />
      {/if}
      <span class="text-sm font-medium">{toast.message}</span>
    </div>
  </div>
{/if}
