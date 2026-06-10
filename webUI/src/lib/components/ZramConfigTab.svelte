<script lang="ts">
  import { 
    Gauge, Plus, Loader2, Info, Trash2, RefreshCw 
  } from 'lucide-svelte';
  import { onMount } from 'svelte';
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
    loading: boolean;
  }>>({});

  // Advanced options toggle for ZRAM Config cards
  let showAdvancedOptions = $state<Record<string, boolean>>({});

  // New ZRAM device form state
  let newDeviceAlgo = $state('zstd');
  let newDeviceSize = $state('2G');
  let loadingNewDevice = $state(false);

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
            loading: false
          };
        } else if (!existing.loading) {
          existing.algo = dev.algo || 'zstd';
          existing.size = formatBytesToSizeString(dev.totalBytes);
          existing.backingDev = dev.backingDev || 'none';
        }
      });
    }
  });

  // Actions
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
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
  <div class="flex items-center gap-3">
    <Gauge class="text-primary" size={22} />
    <div>
      <h2 class="text-lg font-bold">ZRAM Configuration</h2>
      <p class="text-xs text-base-content/60">Create, modify, or remove ZRAM devices</p>
    </div>
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
                      <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" placeholder="e.g. /dev/nvme0n1p3 or none" bind:value={form.backingDev} />
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

      <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
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