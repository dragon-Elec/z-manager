<script lang="ts">
  import { Dialog } from 'bits-ui';
  import { AlertTriangle, CheckCircle2, XCircle, Info, Shield, ShieldAlert, ShieldCheck } from 'lucide-svelte';

  let { health, ram, devices, hibernation, backendConnected } = $props<{
    health: any;
    ram: any;
    devices: any[];
    hibernation: any;
    backendConnected: boolean;
  }>();

  let reportOpen = $state(false);

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

  // Determine health status
  let isCritical = $derived(!health.sysfs_root_accessible || !health.systemd_available);
  let hasWarnings = $derived(health.notes && health.notes.length > 0);

  let statusClass = $derived.by(() => {
    if (!backendConnected) return 'bg-error animate-pulse';
    if (isCritical) return 'bg-error animate-pulse';
    if (hasWarnings) return 'bg-warning';
    return 'bg-primary';
  });

  let statusText = $derived.by(() => {
    if (!backendConnected) return 'Disconnected';
    if (isCritical) return 'Critical Issues';
    if (hasWarnings) return 'Warnings Present';
    return 'System Healthy';
  });

  let systemSummary = $derived.by(() => {
    const devCount = devices.length;
    const devText = devCount === 1 ? '1 device' : `${devCount} devices`;
    const ramSize = formatSize(ram.total);
    const hStat = hibernation.ready ? 'Hibernate Ready' : 'Hibernate Config Needed';
    return `${devText} · ${ramSize} RAM · ${hStat}`;
  });
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm">
  <div class="card-body flex-row items-center justify-between p-4 gap-4">
    <div class="flex items-center gap-3">
      <!-- Status Dot -->
      <span class="w-3.5 h-3.5 rounded-full {statusClass} transition-colors duration-500 shadow-sm shrink-0"></span>
      <div>
        <div class="font-bold text-sm flex items-center gap-1.5">
          {statusText}
        </div>
        <div class="text-xs text-base-content/50 hidden sm:block">
          {systemSummary}
        </div>
      </div>
    </div>

    <div class="flex items-center gap-3 shrink-0">
      <span class="badge badge-sm {backendConnected ? 'badge-success' : 'badge-error'} font-medium">
        {backendConnected ? 'Connected' : 'Disconnected'}
      </span>
      <button 
        class="btn btn-sm btn-ghost font-semibold"
        onclick={() => reportOpen = true}
      >
        View Report
      </button>
    </div>
  </div>
</div>

<!-- Health Report Dialog -->
<Dialog.Root bind:open={reportOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <Dialog.Content class="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-base-content/10 bg-base-100/95 backdrop-blur-md p-6 shadow-lg outline-none max-h-[85vh] overflow-y-auto flex flex-col gap-4">
      <Dialog.Title class="text-xl font-bold flex items-center gap-2">
        {#if isCritical}
          <ShieldAlert class="text-error" size={22} /> System Health Report (Critical)
        {:else if hasWarnings}
          <AlertTriangle class="text-warning" size={22} /> System Health Report (Warnings)
        {:else}
          <ShieldCheck class="text-primary" size={22} /> System Health Report (Healthy)
        {/if}
      </Dialog.Title>

      <div class="space-y-4 my-2 text-sm">
        <!-- Core Diagnostics -->
        <div class="grid grid-cols-2 gap-3 bg-base-200/50 p-3 rounded-xl border border-base-content/5">
          <div>
            <span class="text-xs text-base-content/50 block">Kernel Version</span>
            <span class="font-mono font-semibold">{health.kernel_version || 'Unknown'}</span>
          </div>
          <div>
            <span class="text-xs text-base-content/50 block">ZRAM Devices</span>
            <span class="font-semibold">{health.devices_summary || 'None'}</span>
          </div>
          <div>
            <span class="text-xs text-base-content/50 block">Sysfs Accessible</span>
            <span class="font-semibold flex items-center gap-1">
              {#if health.sysfs_root_accessible}
                <CheckCircle2 class="text-primary" size={14} /> Yes
              {:else}
                <XCircle class="text-error" size={14} /> No
              {/if}
            </span>
          </div>
          <div>
            <span class="text-xs text-base-content/50 block">Systemd Integration</span>
            <span class="font-semibold flex items-center gap-1">
              {#if health.systemd_available}
                <CheckCircle2 class="text-primary" size={14} /> Yes
              {:else}
                <XCircle class="text-error" size={14} /> No
              {/if}
            </span>
          </div>
        </div>

        <!-- ZSwap Status -->
        <div class="p-3 rounded-xl border border-base-content/5 bg-base-200/50">
          <span class="text-xs text-base-content/50 block mb-1">ZSwap Status</span>
          <div class="flex items-center justify-between">
            <span class="font-semibold">
              {#if health.zswap.enabled}
                Enabled <span class="text-warning text-xs">(Conflict Risk)</span>
              {:else if health.zswap.available}
                Disabled (Safe)
              {:else}
                Not Available
              {/if}
            </span>
            <span class="text-xs text-base-content/40 font-mono">{health.zswap.detail}</span>
          </div>
        </div>

        <!-- Recommendations / Notes -->
        <div class="space-y-2">
          <span class="text-xs uppercase tracking-wider text-base-content/50 font-bold block">Recommendations & Notes</span>
          {#if health.notes && health.notes.length > 0}
            <ul class="space-y-2">
              {#each health.notes as note}
                <li class="flex items-start gap-2.5 bg-warning/5 border-l-2 border-warning p-2.5 rounded-r-lg text-xs">
                  <AlertTriangle class="text-warning shrink-0 mt-0.5" size={14} />
                  <span>{note}</span>
                </li>
              {/each}
            </ul>
          {:else}
            <div class="flex items-center gap-2 bg-primary/5 border-l-2 border-primary p-3 rounded-r-lg text-xs">
              <CheckCircle2 class="text-primary shrink-0" size={14} />
              <span>All core systems are operating normally. No conflicts detected.</span>
            </div>
          {/if}
        </div>
      </div>

      <div class="flex justify-end mt-2">
        <Dialog.Close class="btn btn-soft btn-sm">Close</Dialog.Close>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
<style>
  .card {
    contain: paint layout;
    box-sizing: border-box;
  }
  .card, .btn, .badge {
    transform: translate3d(0, 0, 0);
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
  }
</style>
