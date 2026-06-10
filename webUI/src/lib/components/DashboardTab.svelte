<script lang="ts">
  import { Database, Loader2, CheckCircle2, AlertTriangle } from 'lucide-svelte';
  import { Tooltip } from 'bits-ui';
  import HealthStrip from './HealthStrip.svelte';
  import ZramGaugesList from './ZramGaugesList.svelte';
  import SystemPressure from './SystemPressure.svelte';

  let {
    health,
    ram,
    devices,
    swaps,
    hibernation,
    psi,
    backendConnected,
    onConfigureDevice,
    onManageHibernation
  } = $props<{
    health: any;
    ram: any;
    devices: any[];
    swaps: any[];
    hibernation: any;
    psi: any;
    backendConnected: boolean;
    onConfigureDevice: (deviceName: string) => void;
    onManageHibernation: () => void;
  }>();
</script>

<div class="flex flex-col gap-4 animate-fade-in">
  
  <!-- Zone A: Health Strip -->
  <HealthStrip 
    {health} 
    {ram} 
    {devices} 
    {hibernation} 
    {backendConnected} 
  />

  <!-- Flexible Bento Grid Layout -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
    
    <!-- Zone B: ZRAM Live Telemetry (Spans 2 columns on large screens for wide monitoring) -->
    <div class="lg:col-span-2 card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-md font-bold">ZRAM Live Telemetry</h2>
          <p class="text-xs text-base-content/60">Hot Tier · Fast volatile RAM compression</p>
        </div>
        <button 
          class="btn btn-xs btn-ghost font-semibold"
          onclick={() => onConfigureDevice('')}
        >
          Configure
        </button>
      </div>

      {#if devices.length > 0}
        <ZramGaugesList 
          {devices} 
          onConfigureDevice={onConfigureDevice} 
        />
      {:else}
        <div class="py-8 flex flex-col items-center justify-center text-center w-full">
          <Loader2 class="animate-spin text-primary mb-2" size={20} />
          <p class="text-xs text-base-content/60">Waiting for ZRAM telemetry...</p>
        </div>
      {/if}
    </div>

    <!-- Right Column (Stacked Cards: Cold Tier & System Pressure) -->
    <div class="lg:col-span-1 flex flex-col gap-4">
      
      <!-- Zone C: Cold Tier & Swap Summary -->
      <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Database class="text-secondary" size={20} />
            <div>
              <h2 class="text-md font-bold">Cold Tier & Hibernation</h2>
              <p class="text-xs text-base-content/60">Swap & Hibernation readiness</p>
            </div>
          </div>
          <button 
            class="btn btn-xs btn-ghost font-semibold"
            onclick={onManageHibernation}
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
</div>