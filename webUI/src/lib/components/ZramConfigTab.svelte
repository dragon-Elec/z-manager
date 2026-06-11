<script lang="ts">
  import { 
    Gauge, Plus, Loader2, Info, Trash2, RefreshCw, Eye, X
  } from 'lucide-svelte';
  import { onMount } from 'svelte';
  import { Dialog } from 'bits-ui';
  import Select from './Select.svelte';
  import { formatBytesToSizeString } from '../utils';
  import { sendToPython } from '../bridge';

  let {
    devices,
    showToast,
    requestConfirmation
  } = $props<{
    devices: any[];
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
    requestConfirmation: (title: string, desc: string, callback: () => void) => void;
  }>();

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
      devices.forEach((dev) => {
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
        <p class="text-xs text-base-content/60">Create, modify, or remove ZRAM devices</p>
      </div>
    </div>
    <button 
      class="btn btn-xs btn-outline btn-primary font-bold gap-1.5"
      onclick={viewConfigFile}
    >
      <Eye size={14} /> View Configuration File
    </button>
  </div>

  <!-- Two column layout for creation form and active devices list -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start mt-2">
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
                    class="btn btn-2xs btn-error btn-soft font-bold"
                    onclick={() => removeZramDevice(dev.name)}
                  >
                    Remove
                  </button>
                  <button 
                    class="btn btn-2xs btn-neutral btn-soft font-bold"
                    onclick={() => resetZramDevice(dev.name)}
                  >
                    Reset
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2.5">
                <label class="form-control col-span-2">
                  <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Apply Profile</span>
                  <Select 
                    value={selectedProfiles[dev.name] || ''}
                    items={profileItems}
                    onchange={(val) => {
                      selectedProfiles[dev.name] = val;
                      applyProfile(dev.name, val);
                    }}
                  />
                </label>

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
                  <div class="flex flex-col gap-2.5 animate-fade-in bg-base-300/30 p-2.5 rounded-xl border border-base-content/5">
                    <div class="flex flex-col gap-1">
                      <label class="form-control w-full">
                        <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Writeback Backing Device</span>
                        <Select 
                          bind:value={form.backingDev}
                          items={blockDeviceItems}
                        />
                      </label>
                      {#if dev.backingDev && dev.backingDev !== 'none'}
                        <button 
                          type="button"
                          class="btn btn-3xs btn-error btn-soft self-end font-semibold mt-1"
                          onclick={() => clearWriteback(dev.name)}
                        >
                          Clear Writeback Device
                        </button>
                      {/if}
                    </div>

                    <label class="form-control w-full">
                      <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Swap Priority</span>
                      <div class="join w-full">
                        <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => form.swapPriority = Math.max(-1000, Number(form.swapPriority || 0) - 10)}>-</button>
                        <input type="text" class="input input-xs join-item input-bordered w-full text-center font-mono font-semibold" bind:value={form.swapPriority} />
                        <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => form.swapPriority = Math.min(1000, Number(form.swapPriority || 0) + 10)}>+</button>
                      </div>
                    </label>

                    <label class="form-control w-full">
                      <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1 flex justify-between">
                        Host Memory Limit
                        <span class="text-[9px] font-normal lowercase tracking-normal text-base-content/40">Optional (e.g. 1024 or 2G)</span>
                      </span>
                      <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="none" bind:value={form.hostMemLimit} />
                    </label>

                    <label class="form-control w-full">
                      <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Filesystem Type</span>
                      <Select 
                        bind:value={form.fsType}
                        items={[
                          { value: 'swap', label: 'swap (Default)' },
                          { value: 'ext4', label: 'ext4' },
                          { value: 'ext2', label: 'ext2' },
                          { value: 'tmpfs', label: 'tmpfs' }
                        ]}
                      />
                    </label>

                    {#if form.fsType && form.fsType !== 'swap'}
                      <label class="form-control w-full">
                        <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Mount Point</span>
                        <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. /tmp" bind:value={form.mountPoint} />
                      </label>
                    {/if}
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

      <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
        <Plus size={16} /> Create ZRAM Device
      </h3>

      <div class="grid grid-cols-1 gap-3">
        <label class="form-control">
          <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Apply Profile</span>
          <Select 
            value={newDeviceProfile}
            items={profileItems}
            onchange={(val) => {
              newDeviceProfile = val;
              applyNewDeviceProfile(val);
            }}
          />
        </label>

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

        <!-- Progressive Disclosure Fold for New Device Advanced Options -->
        <div class="flex flex-col gap-2">
          <button 
            type="button"
            class="btn btn-2xs btn-ghost justify-start gap-1 p-0 hover:bg-transparent font-bold text-3xs uppercase tracking-wider text-base-content/50"
            onclick={() => showNewAdvancedOptions = !showNewAdvancedOptions}
          >
            <span>{showNewAdvancedOptions ? '▼ hide advanced' : '▶ show advanced'}</span>
          </button>
          
          {#if showNewAdvancedOptions}
            <div class="flex flex-col gap-2.5 animate-fade-in bg-base-300/30 p-2.5 rounded-xl border border-base-content/5">
              <label class="form-control w-full">
                <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Writeback Backing Device</span>
                <Select 
                  bind:value={newDeviceBackingDev}
                  items={blockDeviceItems}
                />
              </label>

              <label class="form-control w-full">
                <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Swap Priority</span>
                <div class="join w-full">
                  <button type="button" class="btn btn-xs join-item btn-neutral font-bold" onclick={() => newDeviceSwapPriority = Math.max(-1000, Number(newDeviceSwapPriority) - 10)}>-</button>
                  <input type="text" class="input input-xs join-item input-bordered w-full text-center font-mono font-semibold" bind:value={newDeviceSwapPriority} />
                  <button type="button" class="btn btn-xs join-item btn-neutral font-bold" onclick={() => newDeviceSwapPriority = Math.min(1000, Number(newDeviceSwapPriority) + 10)}>+</button>
                </div>
              </label>

              <label class="form-control w-full">
                <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1 flex justify-between">
                  Host Memory Limit
                  <span class="text-[9px] font-normal lowercase tracking-normal text-base-content/40">Optional (e.g. 1024 or 2G)</span>
                </span>
                <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="none" bind:value={newDeviceHostMemLimit} />
              </label>

              <label class="form-control w-full">
                <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Filesystem Type</span>
                <Select 
                  bind:value={newDeviceFsType}
                  items={[
                    { value: 'swap', label: 'swap (Default)' },
                    { value: 'ext4', label: 'ext4' },
                    { value: 'ext2', label: 'ext2' },
                    { value: 'tmpfs', label: 'tmpfs' }
                  ]}
                />
              </label>

              {#if newDeviceFsType !== 'swap'}
                <label class="form-control w-full">
                  <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Mount Point</span>
                  <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. /tmp" bind:value={newDeviceMountPoint} />
                </label>
              {/if}
            </div>
          {/if}
        </div>

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

<!-- Profiles Manager Section -->
<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4 mt-6">
  <div class="flex items-center justify-between border-b border-base-content/5 pb-2">
    <div class="flex items-center gap-3">
      <RefreshCw class="text-primary" size={20} />
      <div>
        <h2 class="text-md font-bold">Profiles Manager</h2>
        <p class="text-xs text-base-content/60">Manage pre-defined and custom ZRAM configuration profiles</p>
      </div>
    </div>
    <button class="btn btn-2xs btn-circle btn-ghost" onclick={loadProfiles} title="Refresh Profiles">
      <RefreshCw size={14} class={loadingProfiles ? 'animate-spin' : ''} />
    </button>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- List of available profiles -->
    <div class="lg:col-span-2 flex flex-col gap-2.5 max-h-[360px] overflow-y-auto pr-1">
      {#each Object.entries(availableProfiles) as [name, data]}
        {@const isSystem = systemProfileNames.includes(name)}
        <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-3.5 flex justify-between items-start gap-4">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm">{name}</span>
              {#if isSystem}
                <span class="badge badge-xs badge-neutral font-bold uppercase tracking-wider">System</span>
              {:else}
                <span class="badge badge-xs badge-primary badge-outline font-bold uppercase tracking-wider">Custom</span>
              {/if}
            </div>
            {#if data.description}
              <p class="text-xs text-base-content/60">{data.description}</p>
            {/if}
            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-3xs font-mono uppercase tracking-wider text-base-content/50 font-bold">
              <span>Size: <span class="text-base-content font-semibold">{data['zram-size']}</span></span>
              <span>Algo: <span class="text-base-content font-semibold">{data['compression-algorithm']}</span></span>
              <span>Priority: <span class="text-base-content font-semibold">{data['swap-priority']}</span></span>
            </div>
          </div>

          {#if !isSystem}
            <button 
              class="btn btn-xs btn-error btn-square btn-soft" 
              onclick={() => deleteProfile(name)}
              title="Delete Profile"
            >
              <Trash2 size={13} />
            </button>
          {/if}
        </div>
      {:else}
        <div class="py-12 flex flex-col items-center justify-center text-center w-full bg-base-200/20 border border-base-content/5 rounded-2xl">
          <Info size={24} class="mb-2 opacity-50 text-base-content/40" />
          <p class="text-xs text-base-content/60 font-semibold">No profiles found.</p>
        </div>
      {/each}
    </div>

    <!-- Add custom profile form -->
    <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-4 flex flex-col gap-3 relative">
      {#if loadingProfiles}
        <div class="absolute inset-0 bg-base-100/50 rounded-xl flex items-center justify-center z-10">
          <Loader2 class="animate-spin text-primary" size={20} />
        </div>
      {/if}
      <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
        <Plus size={15} /> Add Custom Profile
      </h3>

      <div class="flex flex-col gap-2.5">
        <label class="form-control">
          <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Profile Name</span>
          <input type="text" class="input input-xs input-bordered w-full font-semibold" placeholder="e.g. My Profile" bind:value={customProfileName} />
        </label>

        <label class="form-control">
          <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Description</span>
          <input type="text" class="input input-xs input-bordered w-full font-semibold" placeholder="e.g. Optimized for low-end device" bind:value={customProfileDesc} />
        </label>

        <div class="grid grid-cols-2 gap-2">
          <label class="form-control">
            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Algorithm</span>
            <Select 
              bind:value={customProfileAlgo}
              items={[
                { value: 'zstd', label: 'zstd' },
                { value: 'lz4', label: 'lz4' },
                { value: 'lzo', label: 'lzo' },
                { value: 'deflate', label: 'deflate' }
              ]}
            />
          </label>

          <label class="form-control">
            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Size</span>
            <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. 2G" bind:value={customProfileSize} />
          </label>
        </div>

        <label class="form-control">
          <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Swap Priority</span>
          <div class="join w-full">
            <button type="button" class="btn btn-xs join-item btn-neutral font-bold" onclick={() => customProfileSwapPriority = Math.max(-1000, Number(customProfileSwapPriority) - 10)}>-</button>
            <input type="text" class="input input-xs join-item input-bordered w-full text-center font-mono font-semibold" bind:value={customProfileSwapPriority} />
            <button type="button" class="btn btn-xs join-item btn-neutral font-bold" onclick={() => customProfileSwapPriority = Math.min(1000, Number(customProfileSwapPriority) + 10)}>+</button>
          </div>
        </label>

        <button 
          class="btn btn-xs btn-primary w-full mt-1.5 font-bold"
          onclick={addCustomProfile}
        >
          Save Profile
        </button>
      </div>
    </div>
  </div>
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
