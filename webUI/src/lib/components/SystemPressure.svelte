<script lang="ts">
  import Sparkline from './Sparkline.svelte';
  import { Activity, HelpCircle, Info, X } from 'lucide-svelte';
  import { Dialog } from 'bits-ui';

  let { psi } = $props<{
    psi: any;
  }>();

  let dialogOpen = $state(false);
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Activity class="text-primary" size={22} />
      <div>
        <h2 class="text-lg font-bold">System Pressure</h2>
        <p class="text-xs text-base-content/60">PSI Stall Information · Last 60 seconds</p>
      </div>
    </div>
    
    <button 
      class="btn btn-xs btn-ghost btn-circle text-base-content/60 hover:text-base-content"
      onclick={() => dialogOpen = true}
      title="PSI Stall Explanations"
    >
      <HelpCircle size={16} />
    </button>
  </div>

  <div class="flex flex-col gap-4 bg-base-200/20 p-3 rounded-xl border border-base-content/5">
    <!-- CPU Pressure -->
    <div class="flex flex-col gap-1.5">
      <Sparkline 
        value={psi?.cpu?.some ?? 0} 
        label="CPU Stall (Some)" 
        colorClass="stroke-secondary"
      />
      <span class="text-[10px] text-base-content/40 font-semibold uppercase px-1">CPU has no 'Full' stall metric</span>
    </div>

    <div class="divider my-0 opacity-40"></div>

    <!-- Memory Pressure Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="flex flex-col gap-1">
        <Sparkline 
          value={psi?.memory?.some ?? 0} 
          label="Memory Stall (Some)" 
          colorClass={psi?.memory?.some > 15 ? 'stroke-warning' : 'stroke-primary'}
        />
        <span class="text-[10px] text-base-content/40 px-1">Tasks delayed waiting for RAM</span>
      </div>
      <div class="flex flex-col gap-1">
        <Sparkline 
          value={psi?.memory?.full ?? 0} 
          label="Memory Stall (Full)" 
          colorClass={psi?.memory?.full > 5 ? 'stroke-error animate-pulse' : 'stroke-secondary'}
        />
        <span class="text-[10px] text-base-content/40 px-1">All tasks blocked (Active Thrashing indicator)</span>
      </div>
    </div>

    <div class="divider my-0 opacity-40"></div>

    <!-- I/O Pressure Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="flex flex-col gap-1">
        <Sparkline 
          value={psi?.io?.some ?? 0} 
          label="I/O Stall (Some)" 
          colorClass="stroke-accent"
        />
        <span class="text-[10px] text-base-content/40 px-1">Tasks delayed waiting for Disk/Swap read/write</span>
      </div>
      <div class="flex flex-col gap-1">
        <Sparkline 
          value={psi?.io?.full ?? 0} 
          label="I/O Stall (Full)" 
          colorClass="stroke-warning"
        />
        <span class="text-[10px] text-base-content/40 px-1">All tasks blocked waiting for storage operations</span>
      </div>
    </div>
  </div>
</div>

<!-- PSI Informational Dialog -->
<Dialog.Root bind:open={dialogOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm" />
    <Dialog.Content class="fixed inset-0 m-auto z-50 h-fit w-full max-w-lg rounded-2xl border border-base-content/10 bg-base-100 p-6 shadow-xl flex flex-col gap-5 text-left">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Info class="text-primary animate-pulse" size={20} />
          <Dialog.Title class="text-lg font-bold">Pressure Stall Information (PSI)</Dialog.Title>
        </div>
        <Dialog.Close class="btn btn-sm btn-ghost btn-circle">
          <X size={16} />
        </Dialog.Close>
      </div>

      <Dialog.Description class="text-xs text-base-content/70 flex flex-col gap-4">
        <p>
          PSI provides a canonical way to measure system resource shortages. It tracks the percentage of time that tasks are stalled waiting for CPU, Memory, or I/O.
        </p>

        <div class="divider my-1"></div>

        <div class="flex flex-col gap-3">
          <div>
            <span class="font-bold text-base-content">Some Stalls:</span>
            <p class="mt-0.5">
              The percentage of time that <strong>at least one task</strong> is stalled waiting for the resource. For example, a single process waiting for disk I/O while other processes continue running.
            </p>
          </div>

          <div>
            <span class="font-bold text-base-content">Full Stalls:</span>
            <p class="mt-0.5">
              The percentage of time that <strong>all non-idle tasks</strong> are stalled waiting for the resource at the same time. This represents a complete loss of throughput (e.g. CPU starvation, swapping). Note: CPU only supports <em>Some</em> stalls.
            </p>
          </div>

          <div>
            <span class="font-bold text-base-content">Memory Thrashing:</span>
            <p class="mt-0.5">
              When memory is fully exhausted, the system spends more time reading and writing pages to swap than executing actual code. A non-zero <strong>Memory Stall (Full)</strong> value is a direct indicator of thrashing.
            </p>
          </div>
        </div>
      </Dialog.Description>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
