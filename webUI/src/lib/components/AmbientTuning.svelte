<script lang="ts">
  import { Tooltip, DropdownMenu } from 'bits-ui';
  import { Sliders, Info, Loader2, ChevronDown } from 'lucide-svelte';

  let {
    tuning,
    localSwappiness = $bindable(60),
    localVfsCachePressure = $bindable(100),
    localCpuGovernor = $bindable('powersave'),
    loadingSwappiness,
    loadingVfsCachePressure,
    loadingCpuGovernor,
    onApplyTuningChange
  } = $props<{
    tuning: any;
    localSwappiness?: number;
    localVfsCachePressure?: number;
    localCpuGovernor?: string;
    loadingSwappiness: boolean;
    loadingVfsCachePressure: boolean;
    loadingCpuGovernor: boolean;
    onApplyTuningChange: (type: 'swappiness' | 'vfs_cache_pressure' | 'cpu_governor', value: any) => void;
  }>();
</script>

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
        onchange={() => onApplyTuningChange('swappiness', localSwappiness)}
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
        onchange={() => onApplyTuningChange('vfs_cache_pressure', localVfsCachePressure)}
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
      
      <DropdownMenu.Root>
        <DropdownMenu.Trigger 
          class="btn btn-sm btn-outline justify-between w-full font-medium"
          disabled={loadingCpuGovernor}
        >
          <span class="truncate">{localCpuGovernor}</span>
          <ChevronDown size={14} class="opacity-60 shrink-0" />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content class="z-50 min-w-[12rem] rounded-xl border border-base-content/10 bg-base-200 p-1 shadow-lg flex flex-col gap-0.5">
            {#each tuning.available_governors as gov}
              <DropdownMenu.Item 
                class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium"
                onclick={() => {
                  localCpuGovernor = gov;
                  onApplyTuningChange('cpu_governor', gov);
                }}
              >
                {gov}
              </DropdownMenu.Item>
            {:else}
              {#each ['powersave', 'performance', 'schedutil'] as gov}
                <DropdownMenu.Item 
                  class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium"
                  onclick={() => {
                    localCpuGovernor = gov;
                    onApplyTuningChange('cpu_governor', gov);
                  }}
                >
                  {gov}
                </DropdownMenu.Item>
              {/each}
            {/each}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>

  </div>
</div>
