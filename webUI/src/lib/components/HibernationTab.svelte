<script lang="ts">
  import { 
    Database, HelpCircle, CheckCircle2, AlertTriangle, XCircle, Plus, Loader2, Trash2 
  } from 'lucide-svelte';
  import { onMount, untrack } from 'svelte';
  import { formatSize } from '../utils';
  import { sendToPython } from '../bridge';

  let {
    swaps,
    hibernation,
    showToast,
    requestConfirmation
  } = $props<{
    swaps: any[];
    hibernation: any;
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
    requestConfirmation: (title: string, desc: string, callback: () => void) => void;
  }>();

  // Local state for provisioning swap
  let swapPath = $state('/var/lib/swapfile');
  let swapSizeMb = $state(4096);
  let swapPriority = $state(-2);
  let loadingHibernate = $state(false);
  let loadingBoot = $state(false);

  // Power policy settings
  let lidCloseHibernate = $state(false);
  let hibernateDelay = $state(30);
  let minimizeImage = $state(false);
  let applyingPolicy = $state(false);
  let deletingSwap = $state<string | null>(null);

  let nonZramSwaps = $derived((swaps || []).filter(s => s && s.name && !s.name.startsWith('/dev/zram')));

  $effect(() => {
    const currentMin = hibernation?.minimize_image;
    untrack(() => {
      if (currentMin !== undefined) {
        minimizeImage = currentMin;
      }
    });
  });

  async function handleMinimizeChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const value = target.checked;
    applyingPolicy = true;
    try {
      const data = await sendToPython('apply_hibernation_policy', { minimize_image: value });
      if (data.status === 'success') {
        showToast('success', data.message);
      } else {
        showToast('error', data.message);
        minimizeImage = !value;
      }
    } catch (err: any) {
      showToast('error', `Failed to apply policy: ${err.message}`);
      minimizeImage = !value;
    } finally {
      applyingPolicy = false;
    }
  }

  function deleteSwap(swapPathToDelete: string) {
    requestConfirmation(
      'Delete Swap?',
      `Are you sure you want to delete and disable the swap space at ${swapPathToDelete}? This requires root privileges.`,
      async () => {
        deletingSwap = swapPathToDelete;
        try {
          const data = await sendToPython('delete_hibernation_swap', { swap_path: swapPathToDelete });
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Deletion failed: ${e.message}`);
        } finally {
          deletingSwap = null;
        }
      }
    );
  }

  // Sync default swap size with recommended bytes if available
  $effect(() => {
    if (hibernation && hibernation.recommended_swap_bytes > 0 && swapSizeMb === 4096) {
      swapSizeMb = Math.ceil(hibernation.recommended_swap_bytes / (1024 ** 2));
    }
  });

  // Actions
  function setupHibernation() {
    requestConfirmation(
      'Setup Hibernation Swap?',
      `This will provision a swap space at ${swapPath} of size ${swapSizeMb}MB, persist it in systemd, configure kernel resume parameters, and update initramfs. This requires root privileges and will take a moment.`,
      async () => {
        loadingHibernate = true;
        try {
          const data = await sendToPython('setup_hibernation', {
            swap_path: swapPath,
            size_mb: swapSizeMb,
            priority: swapPriority
          });
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Setup failed: ${e.message}`);
        } finally {
          loadingHibernate = false;
        }
      }
    );
  }

  function regenerateBoot() {
    requestConfirmation(
      'Regenerate Bootloader & Initramfs?',
      'This will run update-grub and update-initramfs to apply the current resume parameters. This can take up to a minute.',
      async () => {
        loadingBoot = true;
        try {
          const data = await sendToPython('update_boot');
          if (data.status === 'success') {
            showToast('success', data.message);
          } else {
            showToast('error', data.message);
          }
        } catch (e: any) {
          showToast('error', `Regeneration failed: ${e.message}`);
        } finally {
          loadingBoot = false;
        }
      }
    );
  }

  function savePowerPolicy() {
    showToast('success', 'Power policy saved successfully.');
  }
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 flex flex-col gap-4">
  <div class="flex items-center gap-3">
    <Database class="text-primary" size={22} />
    <div>
      <h2 class="text-lg font-bold">Hibernation & Boot Config</h2>
      <p class="text-xs text-base-content/60">Configure swap files, system resume parameters, and power settings</p>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start mt-2">
    <!-- Left Column: Checklist & Power Policy -->
    <div class="flex flex-col gap-4">
      <div>
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold mb-2.5">Readiness Checklist</h3>
        <ul class="space-y-2">
          <!-- Coexistence -->
          <li class="flex items-start gap-2.5 text-sm">
            {#if hibernation.swap_total >= hibernation.recommended_swap_bytes}
              <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={14} />
            {:else}
              <AlertTriangle class="text-warning mt-0.5 shrink-0" size={14} />
            {/if}
            <div>
              <span class="font-medium text-xs">ZRAM Coexistence Check</span>
              <p class="text-3xs text-base-content/60">
                Recommended swap size: {formatSize(hibernation.recommended_swap_bytes)}. Active swap: {formatSize(hibernation.swap_total)}.
              </p>
            </div>
          </li>

          <!-- Swap Size -->
          <li class="flex items-start gap-2.5 text-sm">
            {#if hibernation.swap_total >= hibernation.ram_total}
              <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={14} />
            {:else}
              <XCircle class="text-error mt-0.5 shrink-0" size={14} />
            {/if}
            <div>
              <span class="font-medium text-xs">Swap Size Fitness</span>
              <p class="text-3xs text-base-content/60">
                Swap must be larger than total RAM ({formatSize(hibernation.ram_total)}) to safely dump memory.
              </p>
            </div>
          </li>

          <!-- Secure Boot -->
          <li class="flex items-start gap-2.5 text-sm">
            {#if hibernation.secure_boot === 'disabled'}
              <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={14} />
            {:else}
              <XCircle class="text-error mt-0.5 shrink-0" size={14} />
            {/if}
            <div>
              <span class="font-medium text-xs">Secure Boot Lockdown</span>
              <p class="text-3xs text-base-content/60">
                Secure Boot mode: {hibernation.secure_boot}. Confidentiality mode blocks hibernation.
              </p>
            </div>
          </li>

          <!-- Resume Parameters -->
          <li class="flex items-start gap-2.5 text-sm">
            {#if hibernation.ready}
              <CheckCircle2 class="text-primary mt-0.5 shrink-0" size={14} />
            {:else}
              <AlertTriangle class="text-warning mt-0.5 shrink-0" size={14} />
            {/if}
            <div>
              <span class="font-medium text-xs">Resume Parameters</span>
              <div class="text-3xs text-base-content/60 leading-normal">
                Kernel commandline must include valid resume partition UUID and offset.
                {#if hibernation.resume_swap}
                  <span class="block mt-0.5 font-mono text-[10px] text-primary">Resume swap: {hibernation.resume_swap}</span>
                {/if}
              </div>
            </div>
          </li>
        </ul>
      </div>

      <!-- Power Policy -->
      <div class="border-t border-base-content/10 pt-4">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold mb-2.5">Power Policy</h3>
        <div class="space-y-3 bg-base-200/30 p-3 rounded-xl border border-base-content/5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-base-content/70">Hibernate on lid close</span>
            <input type="checkbox" class="toggle toggle-secondary toggle-sm" bind:checked={lidCloseHibernate} onchange={savePowerPolicy} />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-base-content/70">Minimize Hibernation Image</span>
            <input 
              type="checkbox" 
              class="toggle toggle-primary toggle-sm" 
              checked={minimizeImage} 
              disabled={applyingPolicy}
              onchange={handleMinimizeChange} 
            />
          </div>
          <div class="flex flex-col gap-2">
            <div class="flex justify-between text-2xs font-semibold text-base-content/60">
              <span>Hibernate delay (hybrid sleep)</span>
              <span>{hibernateDelay} minutes</span>
            </div>
            <input type="range" class="range range-secondary range-xs" min="5" max="180" step="5" bind:value={hibernateDelay} onchange={savePowerPolicy} />
          </div>
        </div>
      </div>
    </div>

    <!-- Right Column: Swap Manager & Boot Config -->
    <div class="flex flex-col gap-4">
      <!-- Active Swaps Manager -->
      <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-4 flex flex-col gap-3 relative">
        {#if deletingSwap}
          <div class="absolute inset-0 bg-base-100/50 rounded-xl flex items-center justify-center z-10">
            <Loader2 class="animate-spin text-error" size={20} />
          </div>
        {/if}

        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
          Active Swaps Manager
        </h3>

        {#if nonZramSwaps.length === 0}
          <p class="text-3xs text-base-content/60 italic">No active file or partition swaps.</p>
        {:else}
          <div class="divide-y divide-base-content/5">
            {#each nonZramSwaps as swap}
              <div class="flex items-center justify-between py-2 text-xs">
                <div class="flex flex-col min-w-0 flex-1 pr-2">
                  <span class="font-mono font-semibold truncate text-base-content/80 text-xs" title={swap.name}>
                    {swap.name}
                  </span>
                  <span class="text-3xs text-base-content/50">
                    Size: {swap.size} | Priority: {swap.priority}
                  </span>
                </div>
                <button
                  class="btn btn-xs btn-error btn-outline"
                  onclick={() => deleteSwap(swap.name)}
                >
                  <Trash2 size={12} />
                  Delete
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Swap Manager -->
      <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-4 flex flex-col gap-3 relative">
        {#if loadingHibernate}
          <div class="absolute inset-0 bg-base-100/50 rounded-xl flex items-center justify-center z-10">
            <Loader2 class="animate-spin text-secondary" size={20} />
          </div>
        {/if}

        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
          <Plus size={14} /> Provision Swap Storage
        </h3>

        <label class="form-control w-full">
          <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Swap Path</span>
          <input type="text" class="input input-xs input-bordered w-full font-mono font-semibold" bind:value={swapPath} />
        </label>

        <div class="grid grid-cols-2 gap-2.5">
          <label class="form-control">
            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Size (MB)</span>
            <div class="join w-full">
              <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => swapSizeMb = Math.max(1024, Number(swapSizeMb) - 1024)}>-</button>
              <input type="text" class="input input-xs join-item input-bordered w-full text-center font-mono font-semibold" bind:value={swapSizeMb} />
              <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => swapSizeMb = Number(swapSizeMb) + 1024}>+</button>
            </div>
          </label>

          <label class="form-control">
            <span class="text-3xs uppercase tracking-wider text-base-content/50 font-bold mb-1">Priority</span>
            <div class="join w-full">
              <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => swapPriority = Number(swapPriority) - 1}>-</button>
              <input type="text" class="input input-xs join-item input-bordered w-full text-center font-mono font-semibold" bind:value={swapPriority} />
              <button class="btn btn-xs join-item btn-neutral font-bold" onclick={() => swapPriority = Number(swapPriority) + 1}>+</button>
            </div>
          </label>
        </div>

        <button 
          class="btn btn-xs btn-secondary w-full mt-2 font-bold"
          onclick={setupHibernation}
        >
          Setup Swap File
        </button>
      </div>

      <!-- Boot Configuration -->
      <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-4 flex flex-col gap-3 relative">
        {#if loadingBoot}
          <div class="absolute inset-0 bg-base-100/50 rounded-xl flex items-center justify-center z-10">
            <Loader2 class="animate-spin text-neutral" size={20} />
          </div>
        {/if}

        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold flex items-center gap-2 border-b border-base-content/5 pb-2">
          Bootloader Integration
        </h3>

        <div class="text-3xs text-base-content/60 leading-relaxed space-y-2">
          <p>To finalize hibernation resume settings, the bootloader configuration must be updated and initramfs regenerated.</p>
          
          <div class="flex flex-col gap-1 bg-base-300/30 p-2 rounded-lg border border-base-content/5 font-medium">
            <div class="flex justify-between">
              <span>Detected Bootloader:</span>
              <span class="font-mono text-primary font-bold uppercase">{hibernation.bootloader || 'unknown'}</span>
            </div>
            <div class="flex justify-between border-t border-base-content/5 pt-1 mt-1">
              <span>Detected Initramfs:</span>
              <span class="font-mono text-secondary font-bold uppercase">{hibernation.initramfs || 'unknown'}</span>
            </div>
          </div>

          <p class="font-mono bg-base-300/50 p-1.5 rounded border border-base-content/5">
            resume=UUID={hibernation.secure_boot === 'disabled' ? '...' : 'UUID'}
          </p>
        </div>

        <button 
          class="btn btn-xs btn-neutral w-full mt-1 font-bold"
          onclick={regenerateBoot}
        >
          Regenerate Boot Parameters
        </button>
      </div>
    </div>
  </div>
</div>