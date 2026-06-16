<script lang="ts">
  import { Settings, X, Trash2, Info, Gamepad2, Server, Battery, Box, Shield, Database, HardDrive, Zap, Activity, Terminal, Save, Loader2 } from 'lucide-svelte';
  import { Dialog } from 'bits-ui';
  import Select from './Select.svelte';

  let {
    isProfilesModalOpen = $bindable(false),
    availableProfiles = {},
    addCustomProfile,
    deleteProfile,
    showToast
  } = $props<{
    isProfilesModalOpen: boolean;
    availableProfiles: Record<string, any>;
    addCustomProfile: (name: string, payload: any) => Promise<void>;
    deleteProfile: (name: string) => Promise<void>;
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
  }>();

  let activeProfileTab = $state<'list' | 'create'>('list');
  let loadingProfiles = $state(false);

  // Custom Profile Form State
  let customProfileName = $state('');
  let customProfileDesc = $state('');
  let customProfileAlgo = $state('zstd');
  let customProfileSize = $state('ram / 2');
  let customProfileSwapPriority = $state(100);
  let customProfileIcon = $state('box');

  const availableIcons = [
    { name: 'gamepad', component: Gamepad2, label: 'Gaming' },
    { name: 'server', component: Server, label: 'Server' },
    { name: 'battery', component: Battery, label: 'Power Saver' },
    { name: 'shield', component: Shield, label: 'Security' },
    { name: 'database', component: Database, label: 'Database' },
    { name: 'hard-drive', component: HardDrive, label: 'Storage' },
    { name: 'zap', component: Zap, label: 'Performance' },
    { name: 'activity', component: Activity, label: 'Monitoring' },
    { name: 'terminal', component: Terminal, label: 'Development' },
    { name: 'box', component: Box, label: 'Default' }
  ];

  function getProfileIcon(name: string, metaIcon?: string) {
    if (metaIcon) {
      const match = availableIcons.find(i => i.name === metaIcon);
      if (match) return match.component;
    }
    const lower = name.toLowerCase();
    if (lower.includes('game') || lower.includes('desktop')) return Gamepad2;
    if (lower.includes('server')) return Server;
    if (lower.includes('battery') || lower.includes('power')) return Battery;
    return Box;
  }

  async function handleAddCustomProfile() {
    if (!customProfileName || !customProfileName.trim()) {
      showToast('error', 'Profile name is required');
      return;
    }
    loadingProfiles = true;
    try {
      await addCustomProfile(customProfileName.trim(), {
        'zram-size': customProfileSize,
        'compression-algorithm': customProfileAlgo,
        'swap-priority': Number(customProfileSwapPriority),
        'description': customProfileDesc,
        'icon': customProfileIcon
      });
      customProfileName = '';
      customProfileDesc = '';
      activeProfileTab = 'list';
    } finally {
      loadingProfiles = false;
    }
  }

  async function handleDeleteProfile(name: string) {
    loadingProfiles = true;
    try {
      await deleteProfile(name);
    } finally {
      loadingProfiles = false;
    }
  }
</script>

<Dialog.Root bind:open={isProfilesModalOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm" />
    <Dialog.Content class="fixed inset-0 m-auto z-50 h-[460px] w-full max-w-2xl rounded-2xl border border-base-content/10 bg-base-100 shadow-xl flex flex-col overflow-hidden text-left outline-none">
      
      <!-- Dialog Header -->
      <div class="p-4 border-b border-base-content/5 flex justify-between items-center bg-base-200/10">
        <Dialog.Title class="text-sm font-black flex items-center gap-2">
          <Settings size={18} class="text-primary" /> Profiles Manager
        </Dialog.Title>
        <Dialog.Close class="btn btn-xs btn-ghost btn-circle">
          <X size={14} />
        </Dialog.Close>
      </div>

      <!-- Segmented Tab selector -->
      <div class="tabs tabs-box bg-base-200/30 p-1 flex rounded-none border-b border-base-content/5">
        <button 
          class="tab flex-1 text-xs font-bold py-1.5 {activeProfileTab === 'list' ? 'tab-active' : ''}" 
          onclick={() => activeProfileTab = 'list'}
        >
          Available Profiles
        </button>
        <button 
          class="tab flex-1 text-xs font-bold py-1.5 {activeProfileTab === 'create' ? 'tab-active' : ''}" 
          onclick={() => activeProfileTab = 'create'}
        >
          Create Profile
        </button>
      </div>

      <!-- Content Area -->
      <div class="flex-1 overflow-y-auto p-4 scrollbar-thin relative">
        {#if loadingProfiles}
          <div class="absolute inset-0 bg-base-100/50 flex items-center justify-center z-10">
            <Loader2 class="animate-spin text-primary" size={24} />
          </div>
        {/if}

        {#if activeProfileTab === 'list'}
          <div class="space-y-2.5 max-h-full">
            {#each Object.entries(availableProfiles) as [name, data]}
              {@const isSystem = ['Desktop / Gaming (Recommended)', 'Server (Conservative)'].includes(name)}
              {@const Icon = getProfileIcon(name, (data as any).icon)}
              <div class="bg-base-200/40 border border-base-content/5 rounded-xl p-3 flex justify-between items-center gap-4">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-base-100 border border-base-content/5 rounded-lg">
                    <Icon size={18} class="text-primary" />
                  </div>
                  <div class="flex flex-col">
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-xs">{name}</span>
                      {#if isSystem}
                        <span class="badge badge-[8px] badge-neutral font-bold uppercase py-0.5 px-1">System</span>
                      {:else}
                        <span class="badge badge-[8px] badge-primary badge-outline font-bold uppercase py-0.5 px-1">Custom</span>
                      {/if}
                    </div>
                    {#if (data as any).description}
                      <p class="text-[10px] text-base-content/60 mt-0.5">{(data as any).description}</p>
                    {/if}
                    <div class="flex gap-3 mt-1 text-[10px] font-mono text-base-content/40 font-bold uppercase">
                      <span>Size: <span class="text-base-content">{(data as any)['zram-size']}</span></span>
                      <span>Algo: <span class="text-base-content">{(data as any)['compression-algorithm']}</span></span>
                      <span>Priority: <span class="text-base-content">{(data as any)['swap-priority']}</span></span>
                    </div>
                  </div>
                </div>

                {#if !isSystem}
                  <button 
                    class="btn btn-xs btn-error btn-square btn-soft" 
                    onclick={() => handleDeleteProfile(name)}
                    title="Delete Profile"
                  >
                    <Trash2 size={13} />
                  </button>
                {/if}
              </div>
            {:else}
              <div class="py-12 flex flex-col items-center justify-center text-center w-full">
                <Info size={24} class="mb-2 opacity-50 text-base-content/40" />
                <p class="text-xs text-base-content/60 font-semibold">No profiles registered.</p>
              </div>
            {/each}
          </div>
        {/if}

        {#if activeProfileTab === 'create'}
          <div class="space-y-4 max-h-full">
            <div class="grid grid-cols-2 gap-4">
              <label class="form-control">
                <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Profile Name</span>
                <input type="text" class="input input-xs input-bordered w-full font-bold" placeholder="e.g. Gaming Profile" bind:value={customProfileName} />
              </label>

              <label class="form-control">
                <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Description</span>
                <input type="text" class="input input-xs input-bordered w-full font-bold" placeholder="High priority zram configurations" bind:value={customProfileDesc} />
              </label>
            </div>

            <div class="grid grid-cols-3 gap-4">
              <label class="form-control">
                <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Algorithm</span>
                <Select 
                  bind:value={customProfileAlgo}
                  items={[
                    { value: 'zstd', label: 'zstd' },
                    { value: 'lz4', label: 'lz4' },
                    { value: 'lzo', label: 'lzo' },
                    { value: 'deflate', label: 'deflate' }
                  ]}
                />
              </label>

              <label class="form-control">
                <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Size</span>
                <input type="text" class="input input-xs input-bordered w-full font-mono font-bold" placeholder="e.g. 2G" bind:value={customProfileSize} />
              </label>

              <label class="form-control">
                <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Priority</span>
                <input type="number" class="input input-xs input-bordered w-full font-mono font-bold" bind:value={customProfileSwapPriority} />
              </label>
            </div>

            <!-- Custom Icon Picker -->
            <div class="flex flex-col gap-2">
              <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60">Choose Profile Icon</span>
              <div class="grid grid-cols-6 gap-2 bg-base-200/30 p-2.5 rounded-xl border border-base-content/5">
                {#each availableIcons as icon}
                  {@const IconComp = icon.component}
                  <button 
                    type="button" 
                    class="btn btn-sm btn-ghost p-1 flex flex-col items-center justify-center gap-1 border-2 {customProfileIcon === icon.name ? 'border-primary bg-primary/5' : 'border-transparent'}"
                    onclick={() => customProfileIcon = icon.name}
                    title={icon.label}
                  >
                    <IconComp size={16} class={customProfileIcon === icon.name ? 'text-primary' : 'text-base-content/60'} />
                  </button>
                {/each}
              </div>
            </div>

            <div class="flex justify-end pt-2">
              <button class="btn btn-sm btn-primary font-bold gap-2" onclick={handleAddCustomProfile}>
                <Save size={14} /> Save Profile
              </button>
            </div>
          </div>
        {/if}
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
