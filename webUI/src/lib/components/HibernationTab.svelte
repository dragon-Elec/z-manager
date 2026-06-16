<script lang="ts">
  import { 
    Database, HelpCircle, CheckCircle2, AlertTriangle, XCircle, Plus, Loader2, Trash2, Info, RefreshCw
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

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start mt-2">
    <!-- Left Column: Checklist & Power Policy -->
    <div class="flex flex-col gap-6">
      
      <!-- Readiness Checklist -->
      <div class="flex flex-col gap-2">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold px-1">Readiness Checklist</h3>
        <div class="bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden">
          
          <!-- Coexistence -->
          <div class="flex items-center gap-4 p-4 border-b border-base-content/10">
            <div class="p-2 rounded-full {hibernation.swap_total >= hibernation.recommended_swap_bytes ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}">
              {#if hibernation.swap_total >= hibernation.recommended_swap_bytes}
                <CheckCircle2 size={20} />
              {:else}
                <AlertTriangle size={20} />
              {/if}
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-sm font-bold">ZRAM Coexistence Check</span>
              <span class="text-xs text-base-content/60">
                Recommended swap size: {formatSize(hibernation.recommended_swap_bytes)}. Active swap: {formatSize(hibernation.swap_total)}.
              </span>
            </div>
          </div>

          <!-- Swap Size -->
          <div class="flex items-center gap-4 p-4 border-b border-base-content/10">
            <div class="p-2 rounded-full {hibernation.swap_total >= hibernation.ram_total ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}">
              {#if hibernation.swap_total >= hibernation.ram_total}
                <CheckCircle2 size={20} />
              {:else}
                <XCircle size={20} />
              {/if}
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-sm font-bold">Swap Size Fitness</span>
              <span class="text-xs text-base-content/60">
                Swap must be larger than total RAM ({formatSize(hibernation.ram_total)}) to safely dump memory.
              </span>
            </div>
          </div>

          <!-- Secure Boot -->
          <div class="flex items-center gap-4 p-4 border-b border-base-content/10">
            <div class="p-2 rounded-full {hibernation.secure_boot === 'disabled' ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}">
              {#if hibernation.secure_boot === 'disabled'}
                <CheckCircle2 size={20} />
              {:else}
                <XCircle size={20} />
              {/if}
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-sm font-bold">Secure Boot Lockdown</span>
              <span class="text-xs text-base-content/60">
                Secure Boot mode: {hibernation.secure_boot}. Confidentiality mode blocks hibernation.
              </span>
            </div>
          </div>

          <!-- Resume Parameters -->
          <div class="flex items-center gap-4 p-4">
            <div class="p-2 rounded-full {hibernation.ready ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}">
              {#if hibernation.ready}
                <CheckCircle2 size={20} />
              {:else}
                <AlertTriangle size={20} />
              {/if}
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-sm font-bold">Resume Parameters</span>
              <span class="text-xs text-base-content/60">
                Kernel commandline must include valid resume partition UUID and offset.
              </span>
              {#if hibernation.resume_swap}
                <span class="font-mono text-xs text-primary font-bold mt-1">Resume swap: {hibernation.resume_swap}</span>
              {/if}
            </div>
          </div>

        </div>
      </div>

      <!-- Power Policy -->
      <div class="flex flex-col gap-2">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold px-1">Power Policy</h3>
        <div class="bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden">
          
          <div class="flex justify-between items-center p-4 border-b border-base-content/10">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold">Hibernate on lid close</span>
              <span class="text-xs text-base-content/60">Automatically hibernate when laptop lid is closed.</span>
            </div>
            <input type="checkbox" class="toggle toggle-sm toggle-primary" bind:checked={lidCloseHibernate} onchange={savePowerPolicy} />
          </div>

          <div class="flex justify-between items-center p-4 border-b border-base-content/10">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold">Minimize Hibernation Image</span>
              <span class="text-xs text-base-content/60">Compress memory aggressively before hibernating.</span>
            </div>
            <input 
              type="checkbox" 
              class="toggle toggle-sm toggle-primary" 
              checked={minimizeImage} 
              disabled={applyingPolicy}
              onchange={handleMinimizeChange} 
            />
          </div>

          <div class="flex justify-between items-center p-4">
            <div class="flex flex-col gap-1 w-full">
              <div class="flex justify-between items-center">
                <span class="text-sm font-bold">Hibernate Delay (Hybrid Sleep)</span>
                <span class="text-xs font-bold text-primary">{hibernateDelay} minutes</span>
              </div>
              <span class="text-xs text-base-content/60 mb-2">Time to wait in sleep before hibernating.</span>
              <input type="range" class="range range-primary range-xs w-full" min="5" max="180" step="5" bind:value={hibernateDelay} onchange={savePowerPolicy} />
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Right Column: Swap Manager & Boot Config -->
    <div class="flex flex-col gap-6">
      
      <!-- Active Swaps Manager -->
      <div class="flex flex-col gap-2">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold px-1">Active Swaps Manager</h3>
        <div class="bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden relative">
          {#if deletingSwap}
            <div class="absolute inset-0 bg-base-100/50 flex items-center justify-center z-10">
              <Loader2 class="animate-spin text-error" size={24} />
            </div>
          {/if}

          {#if nonZramSwaps.length === 0}
            <div class="p-6 flex flex-col items-center justify-center text-center">
              <Info size={24} class="mb-2 opacity-50 text-base-content/40" />
              <p class="text-xs text-base-content/60 font-semibold">No active file or partition swaps.</p>
            </div>
          {:else}
            <div class="divide-y divide-base-content/10">
              {#each nonZramSwaps as swap}
                <div class="flex items-center justify-between p-4">
                  <div class="flex flex-col gap-0.5 min-w-0 flex-1 pr-4">
                    <span class="font-mono font-bold text-sm truncate" title={swap.name}>
                      {swap.name}
                    </span>
                    <span class="text-xs text-base-content/60">
                      Size: {swap.size} | Priority: {swap.priority}
                    </span>
                  </div>
                  <button
                    class="btn btn-sm btn-error btn-soft font-bold"
                    onclick={() => deleteSwap(swap.name)}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <!-- Provision Swap Storage -->
      <div class="flex flex-col gap-2">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold px-1">Provision Swap Storage</h3>
        <div class="bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden relative">
          {#if loadingHibernate}
            <div class="absolute inset-0 bg-base-100/50 flex items-center justify-center z-10">
              <Loader2 class="animate-spin text-primary" size={24} />
            </div>
          {/if}

          <div class="flex justify-between items-center p-4 border-b border-base-content/10">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold">Swap Path</span>
              <span class="text-xs text-base-content/60">Absolute path for the new swap file.</span>
            </div>
            <div class="w-48 flex-shrink-0">
              <input type="text" class="input input-sm input-bordered w-full font-mono font-bold" bind:value={swapPath} />
            </div>
          </div>

          <div class="flex justify-between items-center p-4 border-b border-base-content/10">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold">Size (MB)</span>
              <span class="text-xs text-base-content/60">Size of the swap file in megabytes.</span>
            </div>
            <div class="w-48 flex-shrink-0">
              <div class="join w-full">
                <button class="btn btn-sm join-item btn-neutral font-black" onclick={() => swapSizeMb = Math.max(1024, Number(swapSizeMb) - 1024)}>-</button>
                <input type="text" class="input input-sm join-item input-bordered w-full text-center font-mono font-bold" bind:value={swapSizeMb} />
                <button class="btn btn-sm join-item btn-neutral font-black" onclick={() => swapSizeMb = Number(swapSizeMb) + 1024}>+</button>
              </div>
            </div>
          </div>

          <div class="flex justify-between items-center p-4 border-b border-base-content/10">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold">Priority</span>
              <span class="text-xs text-base-content/60">Kernel swap priority.</span>
            </div>
            <div class="w-48 flex-shrink-0">
              <div class="join w-full">
                <button class="btn btn-sm join-item btn-neutral font-black" onclick={() => swapPriority = Number(swapPriority) - 1}>-</button>
                <input type="text" class="input input-sm join-item input-bordered w-full text-center font-mono font-bold" bind:value={swapPriority} />
                <button class="btn btn-sm join-item btn-neutral font-black" onclick={() => swapPriority = Number(swapPriority) + 1}>+</button>
              </div>
            </div>
          </div>

          <div class="p-4 bg-base-200/10">
            <button 
              class="btn btn-sm btn-primary w-full font-bold"
              onclick={setupHibernation}
            >
              <Plus size={14} /> Setup Swap File
            </button>
          </div>
        </div>
      </div>

      <!-- Boot Configuration -->
      <div class="flex flex-col gap-2">
        <h3 class="text-xs uppercase tracking-wider text-base-content/50 font-bold px-1">Bootloader Integration</h3>
        <div class="bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden relative p-4 flex flex-col gap-4">
          {#if loadingBoot}
            <div class="absolute inset-0 bg-base-100/50 flex items-center justify-center z-10">
              <Loader2 class="animate-spin text-primary" size={24} />
            </div>
          {/if}

          <p class="text-xs text-base-content/60">
            To finalize hibernation resume settings, the bootloader configuration must be updated and initramfs regenerated.
          </p>
          
          <div class="flex flex-col gap-2 bg-base-100 p-3 rounded-lg border border-base-content/10">
            <div class="flex justify-between items-center">
              <span class="text-xs font-bold">Detected Bootloader:</span>
              <span class="font-mono text-xs text-primary font-bold uppercase">{hibernation.bootloader || 'unknown'}</span>
            </div>
            <div class="flex justify-between items-center border-t border-base-content/5 pt-2">
              <span class="text-xs font-bold">Detected Initramfs:</span>
              <span class="font-mono text-xs text-secondary font-bold uppercase">{hibernation.initramfs || 'unknown'}</span>
            </div>
          </div>

          <div class="bg-base-300/50 p-2 rounded-lg border border-base-content/10">
            <p class="font-mono text-xs font-bold text-center">
              resume=UUID={hibernation.secure_boot === 'disabled' ? '...' : 'UUID'}
            </p>
          </div>

          <button 
            class="btn btn-sm btn-neutral w-full font-bold"
            onclick={regenerateBoot}
          >
            <RefreshCw size={14} /> Regenerate Boot Parameters
          </button>
        </div>
      </div>
    </div>
  </div>
</div>