<script lang="ts">
  import { Database, Loader2, CheckCircle2, AlertTriangle } from 'lucide-svelte';
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
    updateTick,
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
    updateTick: number;
    onConfigureDevice: (deviceName: string) => void;
    onManageHibernation: () => void;
  }>();
</script>

<div class="flex flex-col gap-4 animate-fade-in w-full">
  
  <!-- Zone A: Health Strip (Full Width) -->
  <HealthStrip 
    {health} 
    {ram} 
    {devices} 
    {hibernation} 
    {backendConnected} 
  />

  <!-- Zone B: ZRAM Live Telemetry (Full Width) -->
  <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4 w-full">
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

  <!-- Row 3: Cold Tier & System Pressure (50/50 Split, Equal Height) -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch w-full">
    
    <!-- Zone C: Cold Tier & Swap Summary (Stretched) -->
    <div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col justify-between gap-4 min-w-[300px]">
      <div>
        <div class="flex items-center justify-between border-b border-base-content/5 pb-2 mb-3">
          <div class="flex items-center gap-2">
            <Database class="text-secondary" size={20} />
            <div>
              <h2 class="text-md font-bold">Cold Tier & Hibernation</h2>
              <p class="text-xs text-base-content/60">Swap & Hibernation readiness</p>
            </div>
          </div>
          <button 
            class="btn btn-xs btn-ghost font-semibold animate-pulse-once"
            onclick={onManageHibernation}
          >
            Manage
          </button>
        </div>

        <div class="flex flex-col gap-3">
          <!-- Readiness Badge -->
          <div class="flex items-center gap-3 bg-base-200/30 border border-base-content/5 p-3 rounded-xl">
            <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50">Readiness:</span>
            
            <div class="tooltip tooltip-right text-xs font-normal normal-case before:max-w-xs before:whitespace-normal" data-tip={hibernation.message}>
              <span class="badge badge-sm {hibernation.ready ? 'badge-primary' : 'badge-warning animate-pulse'} font-semibold gap-1 cursor-help shrink-0">
                {#if hibernation.ready}
                  <CheckCircle2 size={12} /> Ready
                {:else}
                  <AlertTriangle size={12} /> Config Needed
                {/if}
              </span>
            </div>
          </div>

          <!-- Swap Tiers list -->
          <div class="flex flex-col gap-1.5 bg-base-200/30 border border-base-content/5 p-3 rounded-xl">
            <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-0.5">Active Swap Tiers</span>
            {#each swaps as swap}
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs font-mono w-full min-w-0">
                <span class="font-bold text-base-content/80 truncate max-w-[120px]" title={swap.name}>{swap.name}</span>
                <span class="text-base-content/60 text-right shrink-0">{swap.used} / {swap.size} (Pri {swap.priority})</span>
              </div>
            {:else}
              <span class="text-xs text-base-content/40 italic">No disk swap active</span>
            {/each}
          </div>
        </div>
      </div>
    </div>

    <!-- Zone D: System Pressure (Equal Height Card) -->
    <SystemPressure {psi} {updateTick} />

  </div>
</div>