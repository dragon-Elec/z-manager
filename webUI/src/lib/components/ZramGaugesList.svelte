<script lang="ts">
  import { Dialog } from 'bits-ui';
  import ZramGauge from './ZramGauge.svelte';
  import { Info, Settings, HardDrive, AlertTriangle, CheckCircle2, XCircle } from 'lucide-svelte';

  let { devices, onConfigureDevice } = $props<{
    devices: any[];
    onConfigureDevice: (name: string) => void;
  }>();

  let selectedDevice = $state<any | null>(null);
  let statsOpen = $state(false);

  function openStats(device: any) {
    selectedDevice = device;
    statsOpen = true;
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

  let efficiency = $derived(selectedDevice && selectedDevice.comprBytes > 0 
    ? (selectedDevice.origBytes / selectedDevice.comprBytes) 
    : 1.0
  );

  let usagePct = $derived(selectedDevice && selectedDevice.totalBytes > 0 
    ? (selectedDevice.usedBytes / selectedDevice.totalBytes) * 100 
    : 0
  );

  let savedBytes = $derived(selectedDevice 
    ? Math.max(0, selectedDevice.origBytes - selectedDevice.comprBytes) 
    : 0
  );
</script>

<div class="flex flex-wrap gap-6 justify-center md:justify-start">
  {#each devices as dev}
    <ZramGauge 
      name={dev.name}
      algo={dev.algo}
      usedBytes={dev.usedBytes}
      totalBytes={dev.totalBytes}
      origBytes={dev.origBytes}
      comprBytes={dev.comprBytes}
      ramTotal={dev.ramTotal}
      isSwap={dev.isSwap}
      backingDev={dev.backingDev}
      memUsedTotalBytes={dev.memUsedTotalBytes}
      wbNum={dev.wbNum}
      wbFailed={dev.wbFailed}
      onclick={() => openStats(dev)}
      onconfigure={() => onConfigureDevice(dev.name)}
    />
  {:else}
    <div class="flex flex-col items-center justify-center py-8 text-base-content/40 w-full">
      <Info size={32} class="mb-2 opacity-50" />
      <p class="text-sm">No active ZRAM devices detected.</p>
    </div>
  {/each}
</div>

<!-- Quick Stats Dialog -->
<Dialog.Root bind:open={statsOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <Dialog.Content class="fixed inset-0 m-auto z-50 w-full max-w-md h-fit rounded-2xl border border-base-content/10 bg-base-100/95 backdrop-blur-md p-6 shadow-lg outline-none flex flex-col gap-4">
      {#if selectedDevice}
        <Dialog.Title class="text-lg font-bold flex items-center justify-between">
          <span class="font-mono">{selectedDevice.name} Statistics</span>
          <span class="badge badge-sm {selectedDevice.isSwap ? 'badge-success' : 'badge-ghost'}">
            {selectedDevice.isSwap ? 'Active Swap' : 'Unconfigured'}
          </span>
        </Dialog.Title>

        <div class="space-y-4 my-2 text-sm">
          <!-- Compression & Efficiency -->
          <div class="grid grid-cols-2 gap-3 bg-base-200/50 p-3 rounded-xl border border-base-content/5">
            <div>
              <span class="text-xs text-base-content/50 block">Compression Ratio</span>
              <span class="text-lg font-bold text-primary">{efficiency.toFixed(2)}x</span>
            </div>
            <div>
              <span class="text-xs text-base-content/50 block">Algorithm</span>
              <span class="font-mono font-semibold">{selectedDevice.algo}</span>
            </div>
            <div>
              <span class="text-xs text-base-content/50 block">Original Data</span>
              <span class="font-semibold">{formatSize(selectedDevice.origBytes)}</span>
            </div>
            <div>
              <span class="text-xs text-base-content/50 block">Compressed Size</span>
              <span class="font-semibold">{formatSize(selectedDevice.comprBytes)}</span>
            </div>
          </div>

          <!-- Memory & Usage -->
          <div class="space-y-2 bg-base-200/50 p-3 rounded-xl border border-base-content/5">
            <div class="flex justify-between text-xs text-base-content/50">
              <span>ZRAM Pool Usage</span>
              <span class="font-mono font-semibold">{Math.round(usagePct)}%</span>
            </div>
            <progress class="progress progress-primary w-full h-2" value={usagePct} max="100"></progress>
            <div class="flex justify-between text-xs text-base-content/40 pt-1">
              <span>Used: {formatSize(selectedDevice.usedBytes)}</span>
              <span>Total: {formatSize(selectedDevice.totalBytes)}</span>
            </div>
          </div>

          <!-- Savings & Overhead -->
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-2.5 rounded-lg bg-success/5 border border-success/10">
              <span class="text-base-content/50 block mb-0.5">RAM Saved</span>
              <span class="font-bold text-success text-sm">+{formatSize(savedBytes)}</span>
            </div>
            <div class="p-2.5 rounded-lg bg-base-200/50 border border-base-content/5">
              <span class="text-base-content/50 block mb-0.5">Total Memory Overhead</span>
              <span class="font-bold text-sm">{formatSize(selectedDevice.memUsedTotalBytes)}</span>
            </div>
          </div>

          <!-- Writeback Status -->
          {#if selectedDevice.backingDev && selectedDevice.backingDev !== 'none'}
            <div class="p-3 rounded-xl border border-base-content/5 bg-base-200/50 space-y-2">
              <span class="text-xs text-base-content/50 flex items-center gap-1.5 font-bold uppercase tracking-wider">
                <HardDrive size={14} /> Writeback Backing Device
              </span>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span class="text-base-content/50 block">Device Path</span>
                  <span class="font-mono font-semibold">{selectedDevice.backingDev}</span>
                </div>
                <div>
                  <span class="text-base-content/50 block">Pages Written</span>
                  <span class="font-semibold">{selectedDevice.wbNum}</span>
                </div>
                {#if selectedDevice.wbFailed > 0}
                  <div class="col-span-2 flex items-center gap-1.5 text-error mt-1">
                    <AlertTriangle size={13} />
                    <span>{selectedDevice.wbFailed} writeback failures detected</span>
                  </div>
                {/if}
              </div>
            </div>
          {/if}
        </div>

        <div class="flex justify-between items-center mt-2">
          <button 
            class="btn btn-sm btn-primary flex items-center gap-1.5"
            onclick={() => {
              statsOpen = false;
              onConfigureDevice(selectedDevice.name);
            }}
          >
            <Settings size={14} /> Configure Device
          </button>
          <Dialog.Close class="btn btn-soft btn-sm">Close</Dialog.Close>
        </div>
      {/if}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>