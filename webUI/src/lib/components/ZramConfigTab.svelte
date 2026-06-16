<script lang="ts">
  import { 
    Gauge, Plus, Loader2, Info, Trash2, RefreshCw, Eye, X,
    Power, Gamepad2, Scale, Server, Box, SlidersHorizontal,
    Cpu, Settings, Save, FolderOpen, HardDrive
  } from 'lucide-svelte';
  import { onMount } from 'svelte';
  import { Dialog } from 'bits-ui';
  import Select from './Select.svelte';
  import ZramAdvancedView from './ZramAdvancedView.svelte';
  import { formatBytesToSizeString } from '../utils';
  import { sendToPython } from '../bridge';

  let {
    devices,
    ram,
    showToast,
    requestConfirmation
  } = $props<{
    devices: any[];
    ram?: { total: number, used: number };
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
    requestConfirmation: (title: string, desc: string, callback: () => void) => void;
  }>();

  // Simple vs Advanced Mode
  let isAdvancedMode = $state(false);
  
  // Simple View State
  let simpleLoading = $state(false);
  let simpleSizePercent = $state(50);
  let simpleZramEnabled = $state(true);
  let simpleAlgo = $state('zstd');
  let hasSyncedSimpleSize = false;

  $effect(() => {
    if (devices && devices.length > 0) {
      simpleZramEnabled = true;
      const dev = devices[0];
      if (!hasSyncedSimpleSize) {
        simpleAlgo = dev.algo || 'zstd';
        if (dev.totalBytes && ram && ram.total) {
          const rawPercent = (dev.totalBytes / ram.total) * 100;
          // Round to nearest 25 to align with slider grid and prevent snapping bugs
          simpleSizePercent = Math.max(25, Math.min(200, Math.round(rawPercent / 25) * 25));
        }
        hasSyncedSimpleSize = true;
      }
    } else {
      simpleZramEnabled = false;
      hasSyncedSimpleSize = false;
    }
  });

  function applySimplePreset(type: 'desktop' | 'balanced' | 'server' | 'stock') {
    if (type === 'desktop') {
      simpleAlgo = 'zstd';
      simpleSizePercent = 100;
    } else if (type === 'balanced') {
      simpleAlgo = 'zstd';
      simpleSizePercent = 75;
    } else if (type === 'server') {
      simpleAlgo = 'lz4';
      simpleSizePercent = 50;
    } else if (type === 'stock') {
      simpleAlgo = 'zstd';
      simpleSizePercent = 50;
    }
  }

  async function applySimpleConfig() {
    simpleLoading = true;
    try {
      let ramTotal = ram?.total || 0;
      if (ramTotal === 0 && devices.length > 0 && devices[0].ramTotal) {
        ramTotal = devices[0].ramTotal;
      }
      
      let sizeStr = '4G';
      if (ramTotal > 0) {
        const sizeMB = Math.floor((ramTotal * (simpleSizePercent / 100)) / (1024 * 1024));
        sizeStr = `${sizeMB}M`;
      }

      const data = await sendToPython('configure_zram', {
        device: 'zram0',
        size: sizeStr,
        algo: simpleAlgo,
        swapPriority: 100,
        backingDev: 'none',
        hostMemoryLimit: 'none',
        fsType: 'swap',
        mountPoint: ''
      });
      
      if (data.status === 'success') {
        showToast('success', 'ZRAM configured successfully.');
        for (const dev of devices) {
          if (dev.name !== 'zram0') {
            await sendToPython('remove_zram', { device: dev.name });
          }
        }
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Configuration failed: ${e.message}`);
    } finally {
      simpleLoading = false;
    }
  }

  let advancedViewRef: any = $state();

  async function handleSimpleToggle() {
    if (!simpleZramEnabled) {
      simpleLoading = true;
      try {
        for (const dev of devices) {
          await sendToPython('remove_zram', { device: dev.name });
        }
        showToast('success', 'ZRAM disabled successfully.');
      } catch (e: any) {
        showToast('error', `Failed to disable ZRAM: ${e.message}`);
        simpleZramEnabled = true;
      } finally {
        simpleLoading = false;
      }
    } else {
      await applySimpleConfig();
    }
  }

  async function resetSimpleDefaults() {
    simpleAlgo = 'zstd';
    simpleSizePercent = 50;
    await applySimpleConfig();
  }

  // Advanced View State
  let selectedDeviceName = $state<string | null>(null);
  let activeInspectorTab = $state<'alloc' | 'perf' | 'mount'>('alloc');
  let isCreateModalOpen = $state(false);

  $effect(() => {
    if (isAdvancedMode && devices && devices.length > 0 && !selectedDeviceName) {
      selectedDeviceName = devices[0].name;
    }
  });

  // Form states for ZRAM config
  let zramForms = $state<Record<string, {
    algo: string;
    size: string;
    backingDev: string;
    swapPriority: number;
    hostMemLimit: string;
    fsType: string;
    mountPoint: string;
    loading: boolean;
  }>>({});

  // Advanced options toggle for ZRAM Config cards
  let showAdvancedOptions = $state<Record<string, boolean>>({});

  // New ZRAM device form state
  let newDeviceAlgo = $state('zstd');
  let newDeviceSize = $state('2G');
  let newDeviceSwapPriority = $state(100);
  let newDeviceBackingDev = $state('none');
  let newDeviceHostMemLimit = $state('');
  let newDeviceFsType = $state('swap');
  let newDeviceMountPoint = $state('');
  let showNewAdvancedOptions = $state(false);
  let loadingNewDevice = $state(false);

  // Raw configuration viewer state
  let configDialogOpen = $state(false);
  let rawConfigContent = $state('');
  let loadingRawConfig = $state(false);

  // Profiles system state
  let availableProfiles = $state<Record<string, {
    'zram-size': string;
    'compression-algorithm': string;
    'swap-priority': number;
    'description': string;
  }>>({});

  // Block devices state for writeback device picker
  let blockDevices = $state<{ path: string, size: string, model?: string }[]>([]);

  let blockDeviceItems = $derived([
    { value: 'none', label: 'None (Disable Writeback)' },
    ...blockDevices.map(dev => ({
      value: dev.path,
      label: `${dev.path} (${dev.size}${dev.model ? ' - ' + dev.model : ''})`
    }))
  ]);

  let selectedProfiles = $state<Record<string, string>>({});
  let newDeviceProfile = $state('');

  // Add Custom Profile Form state
  let customProfileName = $state('');
  let customProfileSize = $state('2G');
  let customProfileAlgo = $state('zstd');
  let customProfileSwapPriority = $state(100);
  let customProfileDesc = $state('');
  let loadingProfiles = $state(false);

  const systemProfileNames = ['Desktop / Gaming (Recommended)', 'Server (Conservative)'];

  let profileItems = $derived([
    { value: '', label: 'Select a Profile...' },
    ...Object.keys(availableProfiles).map(name => ({
      value: name,
      label: name
    }))
  ]);

  async function loadProfiles() {
    try {
      const data = await sendToPython('list_profiles', {});
      if (data.status === 'success') {
        availableProfiles = data.profiles || {};
      }
    } catch (e: any) {
      console.error('Failed to load profiles:', e);
    }
  }

  async function loadBlockDevices() {
    try {
      const data = await sendToPython('list_block_devices', {});
      if (data.status === 'success') {
        blockDevices = data.devices || [];
      }
    } catch (e: any) {
      console.error('Failed to load block devices:', e);
    }
  }

  onMount(() => {
    loadProfiles();
    loadBlockDevices();
  });

  function applyProfile(deviceName: string, profileName: string) {
    if (!profileName) return;
    const profile = availableProfiles[profileName];
    if (!profile) return;
    const form = zramForms[deviceName];
    if (form) {
      form.algo = profile['compression-algorithm'] || form.algo;
      form.size = profile['zram-size'] || form.size;
      if (profile['swap-priority'] !== undefined && profile['swap-priority'] !== null) {
        form.swapPriority = Number(profile['swap-priority']);
      }
    }
  }

  function applyNewDeviceProfile(profileName: string) {
    if (!profileName) return;
    const profile = availableProfiles[profileName];
    if (profile) {
      newDeviceAlgo = profile['compression-algorithm'] || newDeviceAlgo;
      newDeviceSize = profile['zram-size'] || newDeviceSize;
      if (profile['swap-priority'] !== undefined && profile['swap-priority'] !== null) {
        newDeviceSwapPriority = Number(profile['swap-priority']);
      }
    }
  }

  // Sync form state from telemetry
  $effect(() => {
    if (devices) {
      devices.forEach((dev: any) => {
        const existing = zramForms[dev.name];
        if (!existing) {
          zramForms[dev.name] = {
            algo: dev.algo || 'zstd',
            size: formatBytesToSizeString(dev.totalBytes),
            backingDev: dev.backingDev || 'none',
            swapPriority: dev.swapPriority !== undefined && dev.swapPriority !== null ? dev.swapPriority : 100,
            hostMemLimit: dev.hostMemLimit || '',
            fsType: dev.fsType || 'swap',
            mountPoint: dev.mountPoint || '',
            loading: false
          };
        } else if (!existing.loading) {
          existing.algo = dev.algo || 'zstd';
          existing.size = formatBytesToSizeString(dev.totalBytes);
          existing.backingDev = dev.backingDev || 'none';
          if (dev.swapPriority !== undefined && dev.swapPriority !== null) {
            existing.swapPriority = dev.swapPriority;
          }
          existing.hostMemLimit = dev.hostMemLimit || '';
          existing.fsType = dev.fsType || 'swap';
          existing.mountPoint = dev.mountPoint || '';
        }
      });
    }
  });

  // Actions
  async function viewConfigFile() {
    configDialogOpen = true;
    loadingRawConfig = true;
    try {
      const data = await sendToPython('get_zram_config_raw');
      if (data.status === 'success') {
        rawConfigContent = data.content;
      } else {
        rawConfigContent = `# Error: ${data.message}`;
      }
    } catch (e: any) {
      rawConfigContent = `# Failed to fetch configuration: ${e.message}`;
    } finally {
      loadingRawConfig = false;
    }
  }

  async function applyZramConfig(deviceName: string) {
    const form = zramForms[deviceName];
    if (!form) return;
    form.loading = true;
    try {
      const data = await sendToPython('configure_zram', {
        device: deviceName,
        size: form.size,
        algo: form.algo,
        backingDev: form.backingDev === 'none' ? null : form.backingDev,
        swapPriority: form.swapPriority,
        hostMemoryLimit: form.hostMemLimit || null,
        fsType: form.fsType || null,
        mountPoint: form.mountPoint || null
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

  async function clearWriteback(deviceName: string) {
    requestConfirmation(
      'Clear Writeback Backing Device?',
      `Are you sure you want to clear the writeback backing device for ${deviceName} persistently and live? This requires resetting the device and root privileges.`,
      async () => {
        const form = zramForms[deviceName];
        if (form) form.loading = true;
        try {
          const data = await sendToPython('clear_writeback', { device: deviceName });
          if (data.status === 'success') {
            showToast('success', data.message);
            if (form) form.backingDev = 'none';
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Failed to clear writeback: ${e.message}`);
        } finally {
          if (form) form.loading = false;
        }
      }
    );
  }

  async function createZramDevice() {
    loadingNewDevice = true;
    try {
      const data = await sendToPython('create_zram', {
        size: newDeviceSize,
        algo: newDeviceAlgo,
        swapPriority: newDeviceSwapPriority,
        backingDev: newDeviceBackingDev === 'none' ? null : newDeviceBackingDev,
        hostMemoryLimit: newDeviceHostMemLimit || null,
        fsType: newDeviceFsType || null,
        mountPoint: newDeviceMountPoint || null
      });
      if (data.status === 'success') {
        showToast('success', data.message);
        newDeviceSize = '2G';
        newDeviceSwapPriority = 100;
        newDeviceBackingDev = 'none';
        newDeviceHostMemLimit = '';
        newDeviceFsType = 'swap';
        newDeviceMountPoint = '';
        newDeviceProfile = '';
        isCreateModalOpen = false;
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

  async function addCustomProfile() {
    if (!customProfileName || !customProfileName.trim()) {
      showToast('error', 'Profile name is required');
      return;
    }
    const name = customProfileName.trim();
    if (systemProfileNames.includes(name)) {
      showToast('error', 'Cannot overwrite system profiles');
      return;
    }
    loadingProfiles = true;
    try {
      const data = await sendToPython('save_profile', {
        name,
        data: {
          'zram-size': customProfileSize,
          'compression-algorithm': customProfileAlgo,
          'swap-priority': Number(customProfileSwapPriority),
          'description': customProfileDesc
        }
      });
      if (data.status === 'success') {
        showToast('success', data.message);
        customProfileName = '';
        customProfileDesc = '';
        await loadProfiles();
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Failed to save profile: ${e.message}`);
    } finally {
      loadingProfiles = false;
    }
  }

  async function deleteProfile(name: string) {
    requestConfirmation(
      `Delete Profile ${name}?`,
      `Are you sure you want to delete the custom profile '${name}'?`,
      async () => {
        loadingProfiles = true;
        try {
          const data = await sendToPython('delete_profile', { name });
          if (data.status === 'success') {
            showToast('success', data.message);
            await loadProfiles();
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Failed to delete profile: ${e.message}`);
        } finally {
          loadingProfiles = false;
        }
      }
    );
  }
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Gauge class="text-primary" size={22} />
      <div>
        <h2 class="text-lg font-bold">ZRAM Configuration</h2>
        <p class="text-xs text-base-content/60">Manage compressed memory swap</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      {#if isAdvancedMode}
        <button 
          class="btn btn-xs btn-outline font-bold gap-1.5"
          onclick={() => advancedViewRef?.openProfilesManager()}
        >
          <Settings size={14} /> Profiles Manager
        </button>
        <button 
          class="btn btn-xs btn-primary font-bold gap-1.5"
          onclick={() => advancedViewRef?.addZramDevice()}
        >
          <Plus size={14} /> Add ZRAM Device
        </button>
      {/if}
      <button 
        class="btn btn-xs btn-outline btn-primary font-bold gap-1.5"
        onclick={viewConfigFile}
      >
        <Eye size={14} /> Raw Config
      </button>
      <label class="flex items-center gap-2 cursor-pointer">
        <span class="text-xs font-bold text-base-content/70">Advanced Mode</span>
        <input type="checkbox" class="toggle toggle-sm toggle-primary" bind:checked={isAdvancedMode} />
      </label>
    </div>
  </div>

  {#if !isAdvancedMode}
    <!-- Simple View -->
    <div class="flex flex-col gap-6 mt-2 animate-fade-in">
      
      <!-- Master Toggle & Health -->
      <div class="card bg-base-200/40 border border-base-content/10 p-5 flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="flex items-center gap-4">
          <input type="checkbox" class="toggle toggle-lg toggle-primary" bind:checked={simpleZramEnabled} onchange={handleSimpleToggle} />
          <div class="flex items-center gap-3">
            <div class="p-2 bg-base-100 rounded-lg shadow-sm border border-base-content/5">
              <Power class={simpleZramEnabled ? "text-primary" : "text-base-content/40"} size={24} />
            </div>
            <div>
              <h3 class="font-bold text-lg">{simpleZramEnabled ? 'ZRAM is Active' : 'ZRAM is Disabled'}</h3>
              <p class="text-xs text-base-content/60">Master switch for compressed memory</p>
            </div>
          </div>
        </div>
        
        {#if simpleZramEnabled && devices.length > 0}
          <div class="flex flex-col gap-1 w-full md:w-64">
            <div class="flex justify-between text-xs font-mono font-bold text-base-content/70">
              <span>Usage</span>
              <span>{formatBytesToSizeString(devices.reduce((acc: number, d: any) => acc + (d.origBytes || 0), 0))} / {formatBytesToSizeString(devices.reduce((acc: number, d: any) => acc + (d.totalBytes || 0), 0))}</span>
            </div>
            <progress class="progress progress-primary w-full" value={devices.reduce((acc: number, d: any) => acc + (d.origBytes || 0), 0)} max={devices.reduce((acc: number, d: any) => acc + (d.totalBytes || 0), 0) || 1}></progress>
          </div>
        {/if}
      </div>

      {#if simpleZramEnabled}
        <!-- Size Slider -->
        <div class="flex items-center gap-4 py-2 px-1">
          <span class="text-sm font-bold whitespace-nowrap flex items-center gap-2">
            <SlidersHorizontal size={14} /> ZRAM Size
          </span>
          <div class="relative flex-1">
            <input type="range" min="25" max="200" step="25" bind:value={simpleSizePercent} class="range range-primary range-sm w-full relative z-10" />
            <div class="absolute top-1/2 left-0 right-0 -translate-y-1/2 flex justify-between px-2 pointer-events-none z-20">
              {#each [25, 50, 75, 100, 125, 150, 175, 200] as step}
                <span class="w-1 h-1 rounded-full {simpleSizePercent >= step ? 'bg-primary-content/60' : 'bg-base-content/30'}"></span>
              {/each}
            </div>
          </div>
          <span class="font-mono font-bold text-primary w-12 text-right">{simpleSizePercent}%</span>
        </div>

        <!-- Presets -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <!-- Desktop Preset -->
            <button class="card bg-base-100 border {simpleAlgo === 'zstd' && simpleSizePercent === 100 ? 'border-primary shadow-sm' : 'border-base-content/10 hover:border-primary/30'} transition-all text-left" onclick={() => applySimplePreset('desktop')}>
              <div class="card-body p-4 flex flex-col gap-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center gap-2">
                    <Gamepad2 size={16} class={simpleAlgo === 'zstd' && simpleSizePercent === 100 ? 'text-primary' : 'text-base-content/50'} />
                    <span class="font-bold text-sm">Desktop</span>
                  </div>
                  <span class="badge badge-primary badge-xs font-semibold">Max</span>
                </div>
                <p class="text-xs text-base-content/60">Optimized for responsiveness and heavy multitasking.</p>
                <div class="flex gap-3 mt-1 text-xs font-mono text-base-content/50">
                  <span>Size: 100%</span>
                  <span>Algo: zstd</span>
                </div>
              </div>
            </button>

            <!-- Balanced Preset -->
            <button class="card bg-base-100 border {simpleAlgo === 'zstd' && simpleSizePercent === 75 ? 'border-primary shadow-sm' : 'border-base-content/10 hover:border-primary/30'} transition-all text-left" onclick={() => applySimplePreset('balanced')}>
              <div class="card-body p-4 flex flex-col gap-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center gap-2">
                    <Scale size={16} class={simpleAlgo === 'zstd' && simpleSizePercent === 75 ? 'text-info' : 'text-base-content/50'} />
                    <span class="font-bold text-sm">Balanced</span>
                  </div>
                  <span class="badge badge-info badge-xs font-semibold">Smooth</span>
                </div>
                <p class="text-xs text-base-content/60">A great middle ground for everyday workloads.</p>
                <div class="flex gap-3 mt-1 text-xs font-mono text-base-content/50">
                  <span>Size: 75%</span>
                  <span>Algo: zstd</span>
                </div>
              </div>
            </button>

            <!-- Server Preset -->
            <button class="card bg-base-100 border {simpleAlgo === 'lz4' && simpleSizePercent === 50 ? 'border-primary shadow-sm' : 'border-base-content/10 hover:border-primary/30'} transition-all text-left" onclick={() => applySimplePreset('server')}>
              <div class="card-body p-4 flex flex-col gap-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center gap-2">
                    <Server size={16} class={simpleAlgo === 'lz4' && simpleSizePercent === 50 ? 'text-warning' : 'text-base-content/50'} />
                    <span class="font-bold text-sm">Server</span>
                  </div>
                  <span class="badge badge-warning badge-xs font-semibold">Low CPU</span>
                </div>
                <p class="text-xs text-base-content/60">Minimal CPU overhead and strict memory boundaries.</p>
                <div class="flex gap-3 mt-1 text-xs font-mono text-base-content/50">
                  <span>Size: 50%</span>
                  <span>Algo: lz4</span>
                </div>
              </div>
            </button>

            <!-- Stock Preset -->
            <button class="card bg-base-100 border {simpleAlgo === 'zstd' && simpleSizePercent === 50 ? 'border-primary shadow-sm' : 'border-base-content/10 hover:border-primary/30'} transition-all text-left" onclick={() => applySimplePreset('stock')}>
              <div class="card-body p-4 flex flex-col gap-2">
                <div class="flex justify-between items-start">
                  <div class="flex items-center gap-2">
                    <Box size={16} class={simpleAlgo === 'zstd' && simpleSizePercent === 50 ? 'text-neutral' : 'text-base-content/50'} />
                    <span class="font-bold text-sm">Stock / OS</span>
                  </div>
                  <span class="badge badge-neutral badge-xs font-semibold">Default</span>
                </div>
                <p class="text-xs text-base-content/60">The standard zram-generator default configuration.</p>
                <div class="flex gap-3 mt-1 text-xs font-mono text-base-content/50">
                  <span>Size: 50%</span>
                  <span>Algo: zstd</span>
                </div>
              </div>
            </button>
          </div>

        <!-- Global Actions -->
        <div class="flex justify-end gap-2 mt-2 pt-4 border-t border-base-content/10">
          <button class="btn btn-sm btn-neutral btn-outline" onclick={resetSimpleDefaults} disabled={simpleLoading}>Restore Defaults</button>
          <button class="btn btn-sm btn-primary" onclick={applySimpleConfig} disabled={simpleLoading}>
            {#if simpleLoading}<Loader2 class="animate-spin w-4 h-4" />{/if}
            Apply Changes
          </button>
        </div>
      {/if}
    </div>
  {:else}
    <ZramAdvancedView
      bind:this={advancedViewRef}
      {devices}
      {availableProfiles}
      {blockDevices}
      loadProfiles={loadProfiles}
      loadBlockDevices={loadBlockDevices}
      applyZramConfig={async (deviceName, formVals: any) => {
        // Adapt payload to existing API
        const data = await sendToPython('configure_zram', {
          device: deviceName,
          size: formVals.size,
          algo: formVals.algo,
          backingDev: formVals.backingDev === 'none' ? null : formVals.backingDev,
          swapPriority: formVals.swapPriority,
          hostMemoryLimit: formVals.hostMemoryLimit || null,
          fsType: formVals.fsType || null,
          mountPoint: formVals.mountPoint || null
        });
        if (data.status === 'success') {
          showToast('success', data.message);
        } else {
          throw new Error(data.message);
        }
      }}
      clearWriteback={async (deviceName) => { await clearWriteback(deviceName); }}
      resetZramDevice={async (deviceName) => { await resetZramDevice(deviceName); }}
      removeZramDevice={async (deviceName) => { await removeZramDevice(deviceName); }}
      createZramDevice={async (formVals: any) => {
        const data = await sendToPython('create_zram', {
          size: formVals.size,
          algo: formVals.algo,
          swapPriority: formVals.swapPriority,
          backingDev: formVals.backingDev === 'none' ? null : formVals.backingDev,
          hostMemoryLimit: formVals.hostMemoryLimit || null,
          fsType: formVals.fsType || null,
          mountPoint: formVals.mountPoint || null
        });
        if (data.status === 'success') {
          showToast('success', data.message);
        } else {
          throw new Error(data.message);
        }
      }}
      addCustomProfile={async (name, dataObj) => {
        const data = await sendToPython('save_profile', {
          name,
          data: dataObj
        });
        if (data.status === 'success') {
          showToast('success', data.message);
        } else {
          throw new Error(data.message);
        }
      }}
      deleteProfile={deleteProfile}
      {showToast}
      {requestConfirmation}
    />
  {/if}
</div>

<!-- ZRAM Config Viewer Dialog -->
<Dialog.Root bind:open={configDialogOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm" />
    <Dialog.Content class="fixed inset-0 m-auto z-50 h-fit w-full max-w-lg rounded-2xl border border-base-content/10 bg-base-100 p-6 shadow-xl flex flex-col gap-5 text-left">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Eye class="text-primary" size={20} />
          <Dialog.Title class="text-lg font-bold">zram-generator.conf</Dialog.Title>
        </div>
        <Dialog.Close class="btn btn-sm btn-ghost btn-circle">
          <X size={16} />
        </Dialog.Close>
      </div>

      <Dialog.Description class="text-xs text-base-content/70 flex flex-col gap-3">
        {#if loadingRawConfig}
          <div class="flex items-center justify-center py-12 gap-2">
            <Loader2 class="animate-spin text-primary" size={20} />
            <span>Loading configuration...</span>
          </div>
        {:else}
          <pre class="bg-base-300 p-4 rounded-xl font-mono text-xs overflow-x-auto text-left min-h-[150px] max-h-[350px]">{rawConfigContent}</pre>
        {/if}
      </Dialog.Description>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
