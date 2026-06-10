<script lang="ts">
  import { Tooltip } from 'bits-ui';
  import { Sliders, Info, Loader2, HardDrive, ShieldAlert } from 'lucide-svelte';
  import Select from './Select.svelte';
  import { sendToPython } from '../bridge';

  let {
    tuning,
    showToast
  } = $props<{
    tuning: any;
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
  }>();

  // Cooldown timers to prevent UI flickering on manual tuning changes
  let lastSwappinessChange = 0;
  let lastVfsCachePressureChange = 0;
  let lastCpuGovernorChange = 0;
  let lastZswapChange = 0;
  let lastPsiChange = 0;

  // Local state for tunable controls
  let localSwappiness = $state(60);
  let localVfsCachePressure = $state(100);
  let localCpuGovernor = $state('powersave');
  let localZswapActive = $state(true);
  let localPsiActive = $state(true);

  let loadingSwappiness = $state(false);
  let loadingVfsCachePressure = $state(false);
  let loadingCpuGovernor = $state(false);
  let loadingZswap = $state(false);
  let loadingPsi = $state(false);

  // Sync local controls with incoming tuning telemetry, obeying cooldowns
  $effect(() => {
    const now = Date.now();
    if (tuning) {
      if (!loadingSwappiness && (now - lastSwappinessChange > 2000) && tuning.swappiness !== undefined) {
        localSwappiness = tuning.swappiness;
      }
      if (!loadingVfsCachePressure && (now - lastVfsCachePressureChange > 2000) && tuning.vfs_cache_pressure !== undefined) {
        localVfsCachePressure = tuning.vfs_cache_pressure;
      }
      if (!loadingCpuGovernor && (now - lastCpuGovernorChange > 2000) && tuning.cpu_governor !== undefined) {
        localCpuGovernor = tuning.cpu_governor;
      }
      if (!loadingZswap && (now - lastZswapChange > 2000) && tuning.zswap_active !== undefined) {
        localZswapActive = tuning.zswap_active;
      }
      if (!loadingPsi && (now - lastPsiChange > 2000) && tuning.psi_active !== undefined) {
        localPsiActive = tuning.psi_active;
      }
    }
  });

  async function applyTuningChange(type: 'swappiness' | 'vfs_cache_pressure' | 'cpu_governor', value: any) {
    if (type === 'swappiness') {
      loadingSwappiness = true;
      lastSwappinessChange = Date.now();
    }
    if (type === 'vfs_cache_pressure') {
      loadingVfsCachePressure = true;
      lastVfsCachePressureChange = Date.now();
    }
    if (type === 'cpu_governor') {
      loadingCpuGovernor = true;
      lastCpuGovernorChange = Date.now();
    }

    try {
      const data = await sendToPython('apply_tuning', { [type]: value });
      if (data.status === 'success') {
        showToast('success', data.message);
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Tuning change failed: ${e.message}`);
    } finally {
      if (type === 'swappiness') loadingSwappiness = false;
      if (type === 'vfs_cache_pressure') loadingVfsCachePressure = false;
      if (type === 'cpu_governor') loadingCpuGovernor = false;
    }
  }

  async function applyGrubTuningChange(type: 'zswap_enabled' | 'psi_enabled', value: boolean) {
    if (type === 'zswap_enabled') {
      loadingZswap = true;
      lastZswapChange = Date.now();
    }
    if (type === 'psi_enabled') {
      loadingPsi = true;
      lastPsiChange = Date.now();
    }

    try {
      const data = await sendToPython('apply_tuning', { [type]: value });
      if (data.status === 'success') {
        showToast('success', data.message);
      } else {
        showToast('error', data.message);
      }
    } catch (e: any) {
      showToast('error', `Boot param change failed: ${e.message}`);
    } finally {
      if (type === 'zswap_enabled') loadingZswap = false;
      if (type === 'psi_enabled') loadingPsi = false;
    }
  }
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
  <div class="flex items-center gap-3">
    <Sliders class="text-primary" size={22} />
    <div>
      <h2 class="text-lg font-bold">Kernel & CPU Tuning</h2>
      <p class="text-xs text-base-content/60">Optimize virtual memory swappiness, cache reclaim pressure, and CPU scheduler governor</p>
    </div>
  </div>

  <div class="flex flex-col gap-4">
    <!-- Section 1: Live sysctl and Governor Settings -->
    <div>
      <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold mb-2.5">Live Parameter Control</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 bg-base-200/20 p-3 rounded-xl border border-base-content/5 items-end">
        <!-- Swappiness Slider -->
        <div class="form-control w-full">
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-xs font-semibold text-base-content/60 flex items-center gap-1.5">
              Swappiness
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    Controls how aggressively the kernel swaps memory pages. Lower values reduce swapping (preferring RAM), higher values swap early.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-1.5">
              {#if loadingSwappiness}
                <Loader2 class="animate-spin text-primary" size={12} />
              {/if}
              <span class="text-xs font-mono font-semibold text-primary">{localSwappiness}</span>
            </div>
          </div>
          <input 
            type="range" 
            min="0" 
            max="200" 
            class="range range-xs range-primary" 
            bind:value={localSwappiness}
            onchange={() => applyTuningChange('swappiness', localSwappiness)}
            disabled={loadingSwappiness}
          />
        </div>

        <!-- VFS Cache Pressure Slider -->
        <div class="form-control w-full">
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-xs font-semibold text-base-content/60 flex items-center gap-1.5">
              VFS Cache Pressure
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    Controls the kernel's tendency to reclaim memory used for directory and inode cache. Lower values retain cache, higher values reclaim aggressively.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-1.5">
              {#if loadingVfsCachePressure}
                <Loader2 class="animate-spin text-secondary" size={12} />
              {/if}
              <span class="text-xs font-mono font-semibold text-secondary">{localVfsCachePressure}</span>
            </div>
          </div>
          <input 
            type="range" 
            min="0" 
            max="200" 
            class="range range-xs range-secondary" 
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
          
          <Select 
            bind:value={localCpuGovernor}
            disabled={loadingCpuGovernor}
            onchange={(val) => applyTuningChange('cpu_governor', val)}
            items={tuning?.available_governors?.map((g: string) => ({ value: g, label: g })) || [
              { value: 'powersave', label: 'powersave' },
              { value: 'performance', label: 'performance' },
              { value: 'schedutil', label: 'schedutil' }
            ]}
          />
        </div>
      </div>
    </div>

    <!-- Section 2: Bootloader config (Zswap & PSI toggles) -->
    <div class="border-t border-base-content/10 pt-4">
      <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold mb-2.5">Persistent Boot Parameters</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
        <div class="space-y-3 bg-base-200/20 p-3 rounded-xl border border-base-content/5">
          <!-- Zswap toggle -->
          <div class="flex items-center justify-between text-xs">
            <span class="font-semibold text-base-content/70 flex items-center gap-1.5">
              Kernel ZSwap Cache
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    ZSwap acts as a compressed writeback cache for swaps. When ZRAM is configured, keeping ZSwap enabled wastes CPU cycles compressing pages twice. Disabling is recommended.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-2">
              {#if loadingZswap}
                <Loader2 class="animate-spin text-primary" size={12} />
              {/if}
              <input 
                type="checkbox" 
                class="toggle toggle-primary toggle-xs" 
                bind:checked={localZswapActive} 
                onchange={() => applyGrubTuningChange('zswap_enabled', localZswapActive)} 
                disabled={loadingZswap}
              />
            </div>
          </div>

          <!-- PSI toggle -->
          <div class="flex items-center justify-between text-xs border-t border-base-content/5 pt-2.5">
            <span class="font-semibold text-base-content/70 flex items-center gap-1.5">
              Pressure Stall Information (PSI)
              <Tooltip.Root>
                <Tooltip.Trigger class="cursor-help text-base-content/40 hover:text-base-content"><Info size={13} /></Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 max-w-xs rounded-xl border border-base-content/10 bg-neutral text-neutral-content p-3 text-xs shadow-lg">
                    Enables the kernel PSI subsystem to report CPU, Memory, and I/O pressure stall telemetry. Required for dashboard pressure charts.
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </span>
            <div class="flex items-center gap-2">
              {#if loadingPsi}
                <Loader2 class="animate-spin text-primary" size={12} />
              {/if}
              <input 
                type="checkbox" 
                class="toggle toggle-primary toggle-xs" 
                bind:checked={localPsiActive} 
                onchange={() => applyGrubTuningChange('psi_enabled', localPsiActive)} 
                disabled={loadingPsi}
              />
            </div>
          </div>
        </div>

        <!-- GRUB Warning/Reminder Card -->
        <div class="flex gap-3 bg-warning/5 border border-warning/20 p-3 rounded-xl items-start text-xs">
          <ShieldAlert class="text-warning shrink-0 mt-0.5" size={16} />
          <div>
            <span class="font-bold text-warning/90 block mb-0.5">GRUB Regeneration Required</span>
            <p class="text-base-content/60 leading-normal">
              Changing ZSwap or PSI parameters modifies the persistent GRUB commandline. These values will not take effect on your system until you click **Regenerate Bootloader** under the Hibernation tab.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>