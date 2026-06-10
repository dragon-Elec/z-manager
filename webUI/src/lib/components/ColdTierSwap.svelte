<script lang="ts">
  import { Tooltip } from 'bits-ui';
  import { 
    CheckCircle2, XCircle, AlertTriangle, Info, Plus, Settings, Loader2 
  } from 'lucide-svelte';

  let {
    swaps,
    hibernation,
    swapPath = $bindable('/swapfile'),
    swapSizeMb = $bindable(16384),
    swapPriority = $bindable(0),
    loadingHibernate,
    loadingBoot,
    lidCloseHibernate = $bindable(true),
    hibernateDelay = $bindable(30),
    onSetupHibernation,
    onRegenerateBoot,
    onSavePowerPolicy
  } = $props<{
    swaps: any[];
    hibernation: any;
    swapPath?: string;
    swapSizeMb?: number;
    swapPriority?: number;
    loadingHibernate: boolean;
    loadingBoot: boolean;
    lidCloseHibernate?: boolean;
    hibernateDelay?: number;
    onSetupHibernation: () => void;
    onRegenerateBoot: () => void;
    onSavePowerPolicy: () => void;
  }>();

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
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
  
  <!-- Checklist & Power Policy -->
  <div class="flex flex-col gap-4">
    <div>
      <h3 class="text-md font-semibold mb-2.5 text-base-content/80">Readiness Checklist</h3>
      <ul class="space-y-2">
        <!-- Coexistence -->
        <li class="flex items-start gap-3 text-sm">
          {#if hibernation.swap_total >= hibernation.recommended_swap_bytes}
            <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
          {:else}
            <AlertTriangle class="text-warning mt-0.5 shrink-0" size={16} />
          {/if}
          <div>
            <span class="font-medium">ZRAM Coexistence Check</span>
            <p class="text-xs text-base-content/60">
              Recommended swap size: {formatSize(hibernation.recommended_swap_bytes)}. Active swap: {formatSize(hibernation.swap_total)}.
            </p>
          </div>
        </li>

        <!-- Swap Size -->
        <li class="flex items-start gap-3 text-sm">
          {#if hibernation.swap_total >= hibernation.ram_total}
            <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
          {:else}
            <XCircle class="text-error mt-0.5 shrink-0" size={16} />
          {/if}
          <div>
            <span class="font-medium">Swap Size Fitness</span>
            <p class="text-xs text-base-content/60">
              Swap must be larger than total RAM ({formatSize(hibernation.ram_total)}) to safely dump memory.
            </p>
          </div>
        </li>

        <!-- Secure Boot -->
        <li class="flex items-start gap-3 text-sm">
          {#if hibernation.secure_boot === 'disabled'}
            <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
          {:else}
            <XCircle class="text-error mt-0.5 shrink-0" size={16} />
          {/if}
          <div>
            <span class="font-medium">Secure Boot Lockdown</span>
            <p class="text-xs text-base-content/60">
              Secure Boot mode: {hibernation.secure_boot}. Confidentiality mode blocks hibernation.
            </p>
          </div>
        </li>

        <!-- Resume Parameters -->
        <li class="flex items-start gap-3 text-sm">
          {#if hibernation.ready}
            <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={16} />
          {:else}
            <AlertTriangle class="text-warning mt-0.5 shrink-0" size={16} />
          {/if}
          <div>
            <span class="font-medium">Resume Parameters</span>
            <p class="text-xs text-base-content/60">
              Kernel commandline must include valid resume partition UUID and offset.
            </p>
          </div>
        </li>
      </ul>
    </div>

    <!-- Power Policy -->
    <div class="border-t border-base-content/10 pt-4">
      <h3 class="text-md font-semibold mb-2.5 text-base-content/80">Power Policy</h3>
      <div class="space-y-3 bg-base-200/30 p-3 rounded-xl border border-base-content/5">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">Hibernate on lid close</span>
          <input type="checkbox" class="toggle toggle-secondary" bind:checked={lidCloseHibernate} onchange={onSavePowerPolicy} />
        </div>
        <div class="flex flex-col gap-2">
          <div class="flex justify-between text-xs font-semibold text-base-content/60">
            <span>Hibernate delay (hybrid sleep)</span>
            <span>{hibernateDelay} minutes</span>
          </div>
          <input type="range" class="range range-secondary range-sm" min="5" max="180" step="5" bind:value={hibernateDelay} onchange={onSavePowerPolicy} />
        </div>
      </div>
    </div>
  </div>

  <!-- Swap Manager & Boot Config -->
  <div class="flex flex-col gap-4">
    <!-- Swap Manager -->
    <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-4 flex flex-col gap-3.5 relative">
      {#if loadingHibernate}
        <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
          <Loader2 class="animate-spin text-secondary" size={24} />
        </div>
      {/if}

      <h3 class="text-md font-semibold text-base-content/80 flex items-center gap-2">
        <Plus size={18} /> Provision Swap Storage
      </h3>

      <label class="form-control">
        <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Swap Path</span></div>
        <input type="text" class="input input-sm input-bordered w-full font-mono" bind:value={swapPath} />
      </label>

      <div class="grid grid-cols-2 gap-3">
        <label class="form-control">
          <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Size (MB)</span></div>
          <input type="number" class="input input-sm input-bordered w-full font-mono" bind:value={swapSizeMb} />
        </label>

        <label class="form-control">
          <div class="label py-1"><span class="label-text text-xs font-semibold text-base-content/60">Priority</span></div>
          <input type="number" class="input input-sm input-bordered w-full font-mono" bind:value={swapPriority} />
        </label>
      </div>

      <button 
        class="btn btn-sm btn-secondary w-full mt-2"
        onclick={onSetupHibernation}
      >
        Create & Enable Swap
      </button>
    </div>

    <!-- Boot Config -->
    <div class="bg-base-200/40 border border-base-content/5 rounded-2xl p-5 flex flex-col gap-4 relative">
      {#if loadingBoot}
        <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
          <Loader2 class="animate-spin text-secondary" size={24} />
        </div>
      {/if}

      <h3 class="text-md font-semibold text-base-content/80 flex items-center gap-2">
        <Settings size={18} /> Bootloader Configuration
      </h3>
      
      <div class="text-xs text-base-content/70 space-y-2">
        <p>To finalize hibernation resume settings, the bootloader configuration must be updated and initramfs regenerated.</p>
        <div class="p-3 bg-base-300/50 rounded-xl font-mono text-[11px] leading-relaxed break-all select-all">
          resume=UUID={hibernation.secure_boot === 'disabled' ? '...' : 'UUID'}
        </div>
      </div>

      <button 
        class="btn btn-sm btn-neutral w-full"
        onclick={onRegenerateBoot}
      >
        Apply & Regenerate Initramfs
      </button>
    </div>
  </div>

</div>

