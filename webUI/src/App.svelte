<script lang="ts">
  import { onMount } from 'svelte';
  import { sendToPython, onPython, initSidecarBridge } from '$lib/bridge';
  import ZramGauge from '$lib/components/ZramGauge.svelte';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import { Dialog, Tooltip } from 'bits-ui';
  import { 
    Activity, Settings, HardDrive, Info, CheckCircle2, XCircle, 
    AlertTriangle, Gauge, Sliders, Cpu, Database, RefreshCw, Trash2, 
    Moon, Sun, Loader2, Plus, Check, ChevronDown, ChevronUp
  } from 'lucide-svelte';

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

  // UI state
  let expandedZone = $state<'none' | 'A' | 'B'>('none');
  let settingsOpen = $state(false);
  let lastUpdate = $state<Date | null>(null);
  let sseConnected = $derived(lastUpdate !== null && (Date.now() - lastUpdate.getTime() < 3000));

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

  // Derived properties
  let memoryPressure = $derived(psi?.memory?.some ?? 0);
  let statusDotClass = $derived.by(() => {
    if (memoryPressure > 40) return 'bg-error animate-pulse';
    if (memoryPressure > 15) return 'bg-warning animate-pulse';
    return 'bg-primary';
  });

  let systemSummary = $derived.by(() => {
    const devCount = devices.length;
    const devText = devCount === 1 ? '1 device' : `${devCount} devices`;
    const ramSize = formatSize(ram.total);
    const hStat = hibernation.ready ? 'Hibernate Ready' : 'Hibernate Config Needed';
    return `${devText} · ${ramSize} RAM · ${hStat}`;
  });

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
    });

    // Request initial data
    sendToPython('get_dashboard_data');

    return () => media.removeEventListener('change', listener);
  });

  function changeTheme(mode: string) {
    themeMode = mode;
    localStorage.setItem('zman-theme', mode);
  }

  // Toggle grid expansion
  function toggleZone(zone: 'A' | 'B') {
    if (expandedZone === zone) {
      expandedZone = 'none';
    } else {
      expandedZone = zone;
    }
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
</script>

<Tooltip.Provider>
<div class="min-h-screen text-base-content p-4 md:p-6 flex flex-col gap-6 max-w-7xl mx-auto relative z-10">
  
  <!-- Minimal Top Bar -->
  <header class="navbar card bg-base-100 border border-base-content/10 shadow-sm px-6 py-3 flex items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <!-- Status Dot -->
      <span class="w-3.5 h-3.5 rounded-full {statusDotClass} transition-colors duration-500 shadow-sm"></span>
      <h1 class="text-xl font-bold tracking-tight font-sans">Z-Manager</h1>
    </div>

    <!-- Center Summary -->
    <div class="hidden md:flex text-sm text-base-content/70 font-medium tracking-wide">
      {systemSummary}
    </div>

    <!-- Right Controls -->
    <div class="flex items-center gap-3">
      <!-- Theme Select -->
      <select 
        class="select select-sm select-bordered font-medium focus:outline-none"
        value={themeMode}
        onchange={(e) => changeTheme((e.target as HTMLSelectElement).value)}
      >
        <option value="system">System (Auto)</option>
        {#each availableThemes as theme}
          <option value={theme}>{theme.charAt(0).toUpperCase() + theme.slice(1)}</option>
        {/each}
      </select>

      <!-- Settings Gear -->
      <button 
        class="btn btn-sm btn-ghost btn-circle text-base-content/70 hover:text-base-content"
        onclick={() => settingsOpen = true}
        aria-label="Settings"
      >
        <Settings size={18} />
      </button>
    </div>
  </header>

  <!-- Main Bento Grid Content Area -->
  <main class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
    
    <!-- ZONE A: ZRAM Live Telemetry -->
    <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6 lg:col-span-2">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="flex items-center justify-between cursor-pointer" onclick={() => toggleZone('A')}>
        <div class="flex items-center gap-3">
          <Gauge class="text-primary" size={22} />
          <div>
            <h2 class="text-lg font-bold">ZRAM Live Telemetry</h2>
            <p class="text-xs text-base-content/60">Hot Tier · Fast volatile RAM compression</p>
          </div>
        </div>
        <button class="btn btn-xs btn-ghost btn-circle">
          {#if expandedZone === 'A'}
            <ChevronUp size={16} />
          {:else}
            <ChevronDown size={16} />
          {/if}
        </button>
      </div>

      <!-- At Rest: Gauges Grid -->
      <div class="flex flex-wrap gap-6 justify-center md:justify-start">
        {#each devices as device}
          <ZramGauge
            name={device.name}
            algo={device.algo}
            usedBytes={device.usedBytes}
            totalBytes={device.totalBytes}
            origBytes={device.origBytes}
            comprBytes={device.comprBytes}
            ramTotal={ram.total}
            isSwap={device.isSwap}
            backingDev={device.backingDev}
            wbNum={device.wbNum}
            wbFailed={device.wbFailed}
            memUsedTotalBytes={device.memUsedTotalBytes}
            onclick={() => toggleZone('A')}
            onconfigure={() => {
              if (expandedZone !== 'A') {
                expandedZone = 'A';
              }
            }}
          />
        {:else}
          <div class="py-12 flex flex-col items-center justify-center text-center w-full">
            <Loader2 class="animate-spin text-primary mb-2" size={24} />
            <p class="text-sm text-base-content/60">Waiting for ZRAM telemetry...</p>
          </div>
        {/each}
      </div>

      <!-- Expanded State: Per-device detail forms -->
      {#if expandedZone === 'A' && devices.length > 0}
        <div class="border-t border-base-content/10 pt-6 flex flex-col gap-6">
          <h3 class="text-md font-semibold text-base-content/80">Device Configuration</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                      <select class="select select-sm select-bordered w-full" bind:value={form.algo}>
                        <option value="zstd">zstd (Recommended)</option>
                        <option value="lz4">lz4 (Fastest)</option>
                        <option value="lzo">lzo</option>
                        <option value="deflate">deflate</option>
                      </select>
                    </label>

                    <label class="form-control">
                      <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Size</span></div>
                      <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. 2G or ram/2" bind:value={form.size} />
                    </label>
                  </div>

                  <label class="form-control">
                    <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Writeback (Backing Device)</span></div>
                    <input type="text" class="input input-sm input-bordered w-full font-mono" placeholder="e.g. /dev/nvme0n1p3 or none" bind:value={form.backingDev} />
                  </label>

                  <button 
                    class="btn btn-sm btn-primary w-full mt-2"
                    onclick={() => applyZramConfig(dev.name)}
                  >
                    Apply & Restart Service
                  </button>
                </div>
              {/if}
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- ZONE B: Cold Tier / Hibernate -->
    <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6 lg:col-span-2">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="flex items-center justify-between cursor-pointer" onclick={() => toggleZone('B')}>
        <div class="flex items-center gap-3">
          <Database class="text-secondary" size={22} />
          <div>
            <h2 class="text-lg font-bold">Cold Tier & Hibernation</h2>
            <p class="text-xs text-base-content/60">Persistent Storage · Swap files & partitions</p>
          </div>
        </div>
        <button class="btn btn-xs btn-ghost btn-circle">
          {#if expandedZone === 'B'}
            <ChevronUp size={16} />
          {:else}
            <ChevronDown size={16} />
          {/if}
        </button>
      </div>

      <!-- At Rest: Badges & Summary -->
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

      <!-- Expanded State: Full configuration checklist & controls -->
      {#if expandedZone === 'B'}
        <div class="border-t border-base-content/10 pt-6 grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <!-- Checklist & Power Policy -->
          <div class="flex flex-col gap-6">
            <div>
              <h3 class="text-md font-semibold mb-4 text-base-content/80">Readiness Checklist</h3>
              <ul class="space-y-3">
                <!-- Coexistence -->
                <li class="flex items-start gap-3 text-sm">
                  {#if hibernation.swap_total >= hibernation.recommended_swap_bytes}
                    <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
                  {:else}
                    <XCircle class="text-warning mt-0.5 shrink-0" size={16} />
                  {/if}
                  <div>
                    <span class="font-medium">ZRAM Coexistence Check</span>
                    <p class="text-xs text-base-content/60">
                      Recommended swap size: {formatSize(hibernation.recommended_swap_bytes)}. Active swap: {formatSize(hibernation.swap_total)}.
                    </p>
                  </div>
                </li>

                <!-- Swap Size -->
                <li class="flex items-start gap-3 text-sm">
                  {#if hibernation.swap_total >= hibernation.ram_total}
                    <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
                  {:else}
                    <XCircle class="text-error mt-0.5 shrink-0" size={16} />
                  {/if}
                  <div>
                    <span class="font-medium">Swap Size Fitness</span>
                    <p class="text-xs text-base-content/60">
                      Swap must be larger than total RAM ({formatSize(hibernation.ram_total)}) to safely dump memory.
                    </p>
                  </div>
                </li>

                <!-- Secure Boot -->
                <li class="flex items-start gap-3 text-sm">
                  {#if hibernation.secure_boot === 'disabled'}
                    <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
                  {:else}
                    <XCircle class="text-error mt-0.5 shrink-0" size={16} />
                  {/if}
                  <div>
                    <span class="font-medium">Secure Boot Lockdown</span>
                    <p class="text-xs text-base-content/60">
                      Secure Boot mode: {hibernation.secure_boot}. Confidentiality mode blocks hibernation.
                    </p>
                  </div>
                </li>

                <!-- Resume Parameters -->
                <li class="flex items-start gap-3 text-sm">
                  {#if hibernation.ready}
                    <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
                  {:else}
                    <XCircle class="text-warning mt-0.5 shrink-0" size={16} />
                  {/if}
                  <div>
                    <span class="font-medium">Resume Parameters</span>
                    <p class="text-xs text-base-content/60">
                      Kernel commandline must include valid resume partition UUID and offset.
                    </p>
                  </div>
                </li>
              </ul>
            </div>

            <!-- Power Policy -->
            <div class="border-t border-base-content/10 pt-6">
              <h3 class="text-md font-semibold mb-4 text-base-content/80">Power Policy</h3>
              <div class="space-y-4 bg-base-200/30 p-4 rounded-2xl border border-base-content/5">
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium">Hibernate on lid close</span>
                  <input type="checkbox" class="toggle toggle-secondary" bind:checked={lidCloseHibernate} onchange={savePowerPolicy} />
                </div>
                <div class="flex flex-col gap-2">
                  <div class="flex justify-between text-xs font-semibold text-base-content/60">
                    <span>Hibernate delay (hybrid sleep)</span>
                    <span>{hibernateDelay} minutes</span>
                  </div>
                  <input type="range" class="range range-secondary range-sm" min="5" max="180" step="5" bind:value={hibernateDelay} onchange={savePowerPolicy} />
                </div>
              </div>
            </div>
          </div>

          <!-- Swap Manager & Boot Config -->
          <div class="flex flex-col gap-6">
            <!-- Swap Manager -->
            <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-5 flex flex-col gap-4 relative">
              {#if loadingHibernate}
                <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                  <Loader2 class="animate-spin text-secondary" size={24} />
                </div>
              {/if}

              <h3 class="text-md font-semibold text-base-content/80 flex items-center gap-2">
                <Plus size={18} /> Provision Swap Storage
              </h3>

              <label class="form-control">
                <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Swap Path</span></div>
                <input type="text" class="input input-sm input-bordered w-full font-mono" bind:value={swapPath} />
              </label>

              <div class="grid grid-cols-2 gap-3">
                <label class="form-control">
                  <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Size (MB)</span></div>
                  <input type="number" class="input input-sm input-bordered w-full font-mono" bind:value={swapSizeMb} />
                </label>

                <label class="form-control">
                  <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Priority</span></div>
                  <input type="number" class="input input-sm input-bordered w-full font-mono" bind:value={swapPriority} />
                </label>
              </div>

              <button 
                class="btn btn-sm btn-secondary w-full mt-2"
                onclick={setupHibernation}
              >
                Create & Enable Swap
              </button>
            </div>

            <!-- Boot Config -->
            <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-5 flex flex-col gap-4 relative">
              {#if loadingBoot}
                <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
                  <Loader2 class="animate-spin text-secondary" size={24} />
                </div>
              {/if}

              <h3 class="text-md font-semibold text-base-content/80 flex items-center gap-2">
                <Settings size={18} /> Bootloader Configuration
              </h3>
              
              <div class="text-xs text-base-content/70 space-y-2">
                <p>To finalize hibernation resume settings, the bootloader configuration must be updated and initramfs regenerated.</p>
                <div class="p-3 bg-base-300/50 rounded-xl font-mono text-[11px] leading-relaxed break-all select-all">
                  resume=UUID={hibernation.secure_boot === 'disabled' ? '...' : 'UUID'}
                </div>
              </div>

              <button 
                class="btn btn-sm btn-neutral w-full"
                onclick={regenerateBoot}
              >
                Apply & Regenerate Initramfs
              </button>
            </div>
          </div>

        </div>
      {/if}
    </div>

    <!-- ZONE C: System Pressure -->
    <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
      <div class="flex items-center gap-3">
        <Activity class="text-primary" size={22} />
        <div>
          <h2 class="text-lg font-bold">System Pressure</h2>
          <p class="text-xs text-base-content/60">PSI Stall Information · Last 60 seconds</p>
        </div>
      </div>

      <div class="flex flex-col gap-5 bg-base-200/20 p-4 rounded-2xl border border-base-content/5">
        <!-- CPU Pressure -->
        <Sparkline 
          value={psi?.cpu?.some ?? 0} 
          label="CPU Stall (Some)" 
          colorClass="stroke-secondary"
        />

        <!-- Memory Pressure -->
        <Sparkline 
          value={psi?.memory?.some ?? 0} 
          label="Memory Stall (Some)" 
          colorClass={psi?.memory?.some > 15 ? 'stroke-warning' : 'stroke-primary'}
        />

        <!-- I/O Pressure -->
        <Sparkline 
          value={psi?.io?.some ?? 0} 
          label="I/O Stall (Some)" 
          colorClass="stroke-accent"
        />
      </div>
    </div>

    <!-- ZONE D: Quick Tuning -->
    <div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
      <div class="flex items-center gap-3">
        <Sliders class="text-accent" size={22} />
        <div>
          <h2 class="text-lg font-bold">Quick Tuning</h2>
          <p class="text-xs text-base-content/60">Volatile Kernel Tunables · Applied live</p>
        </div>
      </div>

      <div class="flex flex-col gap-5 bg-base-200/20 p-5 rounded-2xl border border-base-content/5">
        
        <!-- vm.swappiness -->
        <div class="flex flex-col gap-2 relative">
          <div class="flex justify-between items-center text-xs font-semibold">
            <span class="text-base-content/60 flex items-center gap-1.5">
              vm.swappiness 
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    Controls how aggressively the kernel swaps memory pages. Higher values (e.g. 150-200) are optimal for ZRAM.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-2">
              {#if loadingSwappiness}
                <Loader2 class="animate-spin text-accent" size={12} />
              {/if}
              <span class="font-mono text-sm font-bold bg-base-300 px-2 py-0.5 rounded">{localSwappiness}</span>
            </div>
          </div>
          <input 
            type="range" 
            class="range range-accent range-sm" 
            min="0" 
            max="200" 
            step="5" 
            bind:value={localSwappiness}
            onchange={() => applyTuningChange('swappiness', localSwappiness)}
            disabled={loadingSwappiness}
          />
        </div>

        <!-- vm.vfs_cache_pressure -->
        <div class="flex flex-col gap-2 relative">
          <div class="flex justify-between items-center text-xs font-semibold">
            <span class="text-base-content/60 flex items-center gap-1.5">
              vm.vfs_cache_pressure
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    Controls the kernel's tendency to reclaim memory used for directory and inode caches.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-2">
              {#if loadingVfsCachePressure}
                <Loader2 class="animate-spin text-accent" size={12} />
              {/if}
              <span class="font-mono text-sm font-bold bg-base-300 px-2 py-0.5 rounded">{localVfsCachePressure}</span>
            </div>
          </div>
          <input 
            type="range" 
            class="range range-accent range-sm" 
            min="0" 
            max="500" 
            step="10" 
            bind:value={localVfsCachePressure}
            onchange={() => applyTuningChange('vfs_cache_pressure', localVfsCachePressure)}
            disabled={loadingVfsCachePressure}
          />
        </div>

        <!-- CPU Governor -->
        <div class="form-control w-full relative">
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-xs font-semibold text-base-content/60 flex items-center gap-1.5">
              CPU Governor
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    CPU scaling governor. 'performance' forces maximum frequency, 'powersave' balances dynamically.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            {#if loadingCpuGovernor}
              <Loader2 class="animate-spin text-accent" size={12} />
            {/if}
          </div>
          <select 
            class="select select-bordered select-sm w-full font-sans font-medium"
            bind:value={localCpuGovernor}
            onchange={() => applyTuningChange('cpu_governor', localCpuGovernor)}
            disabled={loadingCpuGovernor}
          >
            {#each tuning.available_governors as gov}
              <option value={gov}>{gov}</option>
            {:else}
              <option value="powersave">powersave</option>
              <option value="performance">performance</option>
              <option value="schedutil">schedutil</option>
            {/each}
          </select>
        </div>

      </div>
    </div>

  </main>

  <!-- Bottom Status line -->
  <footer class="mt-auto py-4 text-center text-xs text-base-content/40 flex flex-col md:flex-row items-center justify-between gap-2 border-t border-base-content/5">
    <div class="flex items-center gap-2">
      <span class="inline-block w-2 h-2 rounded-full {sseConnected ? 'bg-primary' : 'bg-error'}"></span>
      <span>{sseConnected ? 'Native Bridge Connected' : 'Connecting...'}</span>
    </div>
    <span>Z-Manager v0.9.0-beta · Built for Calm Control</span>
  </footer>

</div>
</Tooltip.Provider>

<!-- Portal-based Settings Drawer -->
<Dialog.Root bind:open={settingsOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <Dialog.Content class="fixed right-0 top-0 bottom-0 z-50 w-80 border-l border-base-content/10 bg-base-100/90 backdrop-blur-md p-6 shadow-lg outline-none flex flex-col justify-between">
      <div>
        <Dialog.Title class="text-xl font-bold flex items-center gap-2 mb-6">
          <Settings size={20} /> Settings
        </Dialog.Title>
        
        <div class="space-y-6">
          <!-- Connection Status -->
          <div class="flex flex-col gap-2">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Backend Connection</span>
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full {sseConnected ? 'bg-primary' : 'bg-error'}"></span>
              <span class="text-sm font-medium">{sseConnected ? 'Connected (Native)' : 'Disconnected'}</span>
            </div>
          </div>

          <!-- Theme Override -->
          <div class="flex flex-col gap-2">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Theme Mode</span>
            <select 
              class="select select-sm select-bordered w-full font-medium focus:outline-none"
              value={themeMode}
              onchange={(e) => changeTheme((e.target as HTMLSelectElement).value)}
            >
              <option value="system">System (Auto)</option>
              {#each availableThemes as theme}
                <option value={theme}>{theme.charAt(0).toUpperCase() + theme.slice(1)}</option>
              {/each}
            </select>
          </div>

          <!-- App Version -->
          <div class="flex flex-col gap-1">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Version</span>
            <span class="text-sm font-mono text-base-content/80">v0.9.0-beta</span>
          </div>
        </div>
      </div>
      
      <Dialog.Close class="btn btn-soft w-full mt-6">Close</Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>

<!-- Portal-based Confirmation Dialog -->
<Dialog.Root bind:open={confirmOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <Dialog.Content class="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-base-content/10 bg-base-100/95 backdrop-blur-md p-6 shadow-lg outline-none">
      <Dialog.Title class="text-lg font-bold flex items-center gap-2 text-warning">
        <AlertTriangle size={20} /> {confirmTitle}
      </Dialog.Title>
      <Dialog.Description class="mt-2 text-sm text-base-content/70">
        {confirmDesc}
      </Dialog.Description>
      <div class="mt-6 flex justify-end gap-3">
        <Dialog.Close class="btn btn-soft">Cancel</Dialog.Close>
        <button class="btn btn-warning" onclick={() => confirmAction?.()}>Confirm</button>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>

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

<style>
  /* Subtle slide-in animation for toast */
  @keyframes slideIn {
    from {
      transform: translateY(1rem);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
  .animate-slide-in {
    animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
</style>
