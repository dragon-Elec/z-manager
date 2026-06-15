<script lang="ts">
  import { 
    Cpu, Plus, Settings, SlidersHorizontal, Info, Play, Save, X, Trash2, 
    RefreshCw, Loader2, Gamepad2, Scale, Server, Box, Battery, Shield, Database,
    HardDrive, Zap, Activity, Terminal
  } from 'lucide-svelte';
  import { Dialog } from 'bits-ui';
  import Select from './Select.svelte';

  let {
    devices = [],
    availableProfiles = {},
    blockDevices = [],
    loadProfiles,
    loadBlockDevices,
    applyZramConfig,
    clearWriteback,
    resetZramDevice,
    removeZramDevice,
    createZramDevice,
    addCustomProfile,
    deleteProfile,
    showToast,
    requestConfirmation
  } = $props<{
    devices: any[];
    availableProfiles: Record<string, any>;
    blockDevices: any[];
    loadProfiles: () => Promise<void>;
    loadBlockDevices: () => Promise<void>;
    applyZramConfig: (deviceName: string, options?: any) => Promise<void>;
    clearWriteback: (deviceName: string) => Promise<void>;
    resetZramDevice: (deviceName: string) => Promise<void>;
    removeZramDevice: (deviceName: string) => Promise<void>;
    createZramDevice: (payload: any) => Promise<void>;
    addCustomProfile: (name: string, payload: any) => Promise<void>;
    deleteProfile: (name: string) => Promise<void>;
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
    requestConfirmation: (title: string, desc: string, callback: () => void) => void;
  }>();

  // State Management
  let selectedDeviceName = $state<string | null>(null);
  let activeInspectorTab = $state<'alloc' | 'perf' | 'mount'>('alloc');
  let applyMode = $state<'both' | 'live' | 'persist'>('both');
  
  // Dirty state tracking (key is deviceName, value is true/false or set of fields)
  let dirtyFields = $state<Record<string, Record<string, boolean>>>({});
  
  // Custom forms state mimicking original backend bindings but isolated from live updates
  let forms = $state<Record<string, {
    algo: string;
    size: string;
    backingDev: string;
    swapPriority: number;
    hostMemLimit: string;
    fsType: string;
    mountPoint: string;
    loading: boolean;
  }>>({});

  // Initialize selected device
  $effect(() => {
    if (devices && devices.length > 0 && !selectedDeviceName) {
      selectedDeviceName = devices[0].name;
    }
  });

  // Keep forms synced with incoming telemetry ONLY if the field is not dirty
  // Keep forms synced with incoming telemetry ONLY if the field is not dirty
  $effect(() => {
    if (devices) {
      devices.forEach((dev: any) => {
        if (!forms[dev.name]) {
          forms[dev.name] = {
            algo: dev.algo || 'zstd',
            size: formatBytesToSizeString(dev.totalBytes) || '2G',
            backingDev: dev.backingDev || 'none',
            swapPriority: dev.swapPriority !== undefined ? dev.swapPriority : 100,
            hostMemLimit: dev.hostMemLimit || '',
            fsType: dev.fsType || 'swap',
            mountPoint: dev.mountPoint || '',
            loading: false
          };
          dirtyFields[dev.name] = {};
        } else {
          const form = forms[dev.name];
          const dirty = dirtyFields[dev.name] || {};
          
          if (!dirty.algo && !form.loading) form.algo = dev.algo || 'zstd';
          if (!dirty.size && !form.loading) form.size = formatBytesToSizeString(dev.totalBytes) || '2G';
          if (!dirty.backingDev && !form.loading) form.backingDev = dev.backingDev || 'none';
          if (!dirty.swapPriority && !form.loading && dev.swapPriority !== undefined) {
            form.swapPriority = dev.swapPriority;
          }
          if (!dirty.hostMemLimit && !form.loading) form.hostMemLimit = dev.hostMemLimit || '';
          if (!dirty.fsType && !form.loading) form.fsType = dev.fsType || 'swap';
          if (!dirty.mountPoint && !form.loading) form.mountPoint = dev.mountPoint || '';
        }
      });
    }
  });

  // Switch guard: alert on unsaved modifications
  function selectDevice(name: string) {
    if (selectedDeviceName && selectedDeviceName !== name) {
      const dirty = dirtyFields[selectedDeviceName];
      const hasUnsaved = dirty && Object.values(dirty).some(v => v === true);
      if (hasUnsaved) {
        requestConfirmation(
          'Unsaved Changes',
          `Device ${selectedDeviceName} has unsaved changes. Switching will discard them. Do you want to continue?`,
          () => {
            // Revert dirty state of current device
            revertChanges(selectedDeviceName!);
            selectedDeviceName = name;
          }
        );
        return;
      }
    }
    selectedDeviceName = name;
  }

  // Mark field dirty helper
  function markDirty(fieldName: string) {
    if (!selectedDeviceName) return;
    if (!dirtyFields[selectedDeviceName]) {
      dirtyFields[selectedDeviceName] = {};
    }
    dirtyFields[selectedDeviceName][fieldName] = true;
  }

  // Check if current active device has unsaved changes
  let isCurrentDeviceDirty = $derived(() => {
    if (!selectedDeviceName || !dirtyFields[selectedDeviceName]) return false;
    return Object.values(dirtyFields[selectedDeviceName]).some(v => v === true);
  });

  // Revert changes
  function revertChanges(deviceName: string) {
    const dev = devices.find((d: any) => d.name === deviceName);
    const form = forms[deviceName];
    if (dev && form) {
      form.algo = dev.algo || 'zstd';
      form.size = formatBytesToSizeString(dev.totalBytes) || '2G';
      form.backingDev = dev.backingDev || 'none';
      form.swapPriority = dev.swapPriority !== undefined ? dev.swapPriority : 100;
      form.hostMemLimit = dev.hostMemLimit || '';
      form.fsType = dev.fsType || 'swap';
      form.mountPoint = dev.mountPoint || '';
      dirtyFields[deviceName] = {};
    }
  }
  async function triggerApply(deviceName: string) {
    const form = forms[deviceName];
    if (!form) return;
    
    // Client-side validations
    if (!form.size.trim() || !/^\d+(\.\d+)?[GMKgmk]?$/.test(form.size)) {
      showToast('error', 'Invalid Size format (e.g. 2G, 512M).');
      return;
    }
    if (isNaN(form.swapPriority) || form.swapPriority < -1000 || form.swapPriority > 1000) {
      showToast('error', 'Priority must be an integer between -1000 and 1000.');
      return;
    }
    if (form.fsType !== 'swap' && (!form.mountPoint || !form.mountPoint.startsWith('/'))) {
      showToast('error', 'Mount point must be an absolute path starting with "/".');
      return;
    }

    form.loading = true;
    try {
      await applyZramConfig(deviceName, {
        size: form.size,
        algo: form.algo,
        backingDev: form.backingDev === 'none' ? null : form.backingDev,
        swapPriority: Number(form.swapPriority),
        hostMemoryLimit: form.hostMemLimit || null,
        fsType: form.fsType || null,
        mountPoint: form.mountPoint || null,
        mode: applyMode
      });
      // Clear dirty states on success
      dirtyFields[deviceName] = {};
    } catch (e: any) {
      showToast('error', e.message || 'Operation failed');
    } finally {
      form.loading = false;
    }
  }
  // Dropdown list formatting
  let blockDeviceItems = $derived([
    { value: 'none', label: 'None (Disable Writeback)' },
    ...blockDevices.map((dev: any) => ({
      value: dev.path,
      label: `${dev.path} (${dev.size}${dev.model ? ' - ' + dev.model : ''})`
    }))
  ]);

  let profileItems = $derived([
    { value: '', label: 'Apply Profile template...' },
    ...Object.keys(availableProfiles).map(name => ({
      value: name,
      label: name
    }))
  ]);

  // Apply a profile to current form state
  function handleProfileSelect(profileName: string) {
    if (!profileName || !selectedDeviceName) return;
    const profile = availableProfiles[profileName];
    if (!profile) return;
    const form = forms[selectedDeviceName];
    if (form) {
      form.algo = profile['compression-algorithm'] || form.algo;
      form.size = profile['zram-size'] || form.size;
      if (profile['swap-priority'] !== undefined && profile['swap-priority'] !== null) {
        form.swapPriority = Number(profile['swap-priority']);
      }
      // Mark fields dirty
      markDirty('algo');
      markDirty('size');
      markDirty('swapPriority');
      showToast('info', `Profile "${profileName}" applied to configuration fields.`);
    }
  }

  // Helper formatting size bytes
  function formatBytesToSizeString(bytes?: number): string {
    if (!bytes) return '2G';
    const g = bytes / (1024 * 1024 * 1024);
    if (g >= 1) return `${Math.round(g * 10) / 10}G`;
    const m = bytes / (1024 * 1024);
    return `${Math.round(m)}M`;
  }

  // Dialog profiles state
  let isProfilesModalOpen = $state(false);
  let activeProfileTab = $state<'list' | 'create'>('list');
  let customProfileName = $state('');
  let customProfileDesc = $state('');
  let customProfileSize = $state('2G');
  let customProfileAlgo = $state('zstd');
  let customProfileSwapPriority = $state(100);
  let customProfileIcon = $state('gamepad-2');
  let loadingProfileDialog = $state(false);

  const availableIcons = [
    { name: 'gamepad-2', component: Gamepad2, label: 'Gaming / Responsiveness' },
    { name: 'scale', component: Scale, label: 'Balanced / Office' },
    { name: 'server', component: Server, label: 'Server / Cache' },
    { name: 'box', component: Box, label: 'Default / OS Default' },
    { name: 'battery', component: Battery, label: 'Power Saver' },
    { name: 'shield', component: Shield, label: 'Secure' },
    { name: 'database', component: Database, label: 'Database' },
    { name: 'hard-drive', component: HardDrive, label: 'Storage' },
    { name: 'zap', component: Zap, label: 'High Speed' },
    { name: 'activity', component: Activity, label: 'Performance' },
    { name: 'terminal', component: Terminal, label: 'Developer' }
  ];

  async function createCustomProfile() {
    if (!customProfileName.trim()) {
      showToast('error', 'Profile Name is required.');
      return;
    }
    loadingProfileDialog = true;
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
      await loadProfiles();
    } catch (e: any) {
      showToast('error', e.message || 'Failed to create profile');
    } finally {
      loadingProfileDialog = false;
    }
  }

  // Pre-fill creation from current configuration template
  function openSaveAsProfile() {
    if (!selectedDeviceName) return;
    const form = forms[selectedDeviceName];
    if (form) {
      customProfileSize = form.size;
      customProfileAlgo = form.algo;
      customProfileSwapPriority = form.swapPriority;
      customProfileName = `Profile-${selectedDeviceName}`;
      customProfileDesc = `Profile copied from ${selectedDeviceName} configuration template.`;
      customProfileIcon = 'gamepad-2';
      activeProfileTab = 'create';
      isProfilesModalOpen = true;
    }
  }

  // New Device creation inline in sidebar
  async function triggerCreateDraft() {
    const nextIdx = devices.length;
    const proposedName = `zram${nextIdx}`;
    
    // Add draft directly into telemetry/forms list
    if (forms[proposedName]) {
      showToast('error', `A draft or device named ${proposedName} already exists.`);
      return;
    }
    
    forms[proposedName] = {
      algo: 'zstd',
      size: '2G',
      backingDev: 'none',
      swapPriority: 100,
      hostMemLimit: '',
      fsType: 'swap',
      mountPoint: '',
      loading: false
    };
    
    dirtyFields[proposedName] = {
      algo: true,
      size: true,
      swapPriority: true
    };

    // Synthesize a draft device block locally
    devices.push({
      name: proposedName,
      isDraft: true,
      totalBytes: 2 * 1024 * 1024 * 1024,
      origBytes: 0,
      algo: 'zstd',
      swapPriority: 100,
      fsType: 'swap',
      mountPoint: ''
    });

    selectedDeviceName = proposedName;
    showToast('success', `Draft ${proposedName} added. Complete parameters in right panel and apply.`);
  }

  // Apply wrapper that handles creation logic for drafts too
  async function handleApplyOrSave(deviceName: string) {
    const form = forms[deviceName];
    if (!form) return;
    const isDraft = devices.find((d: any) => d.name === deviceName)?.isDraft;
    
    if (isDraft) {
      form.loading = true;
      try {
        await createZramDevice({
          size: form.size,
          algo: form.algo,
          swapPriority: form.swapPriority,
          backingDev: form.backingDev === 'none' ? null : form.backingDev,
          hostMemoryLimit: form.hostMemLimit || null,
          fsType: form.fsType || null,
          mountPoint: form.mountPoint || null
        });
        
        // Remove draft state flag once applied
        const idx = devices.findIndex((d: any) => d.name === deviceName);
        if (idx !== -1) {
          devices[idx].isDraft = false;
        }
        dirtyFields[deviceName] = {};
      } catch (e: any) {
        showToast('error', e.message || 'Draft creation failed');
      } finally {
        form.loading = false;
      }
    } else {
      await triggerApply(deviceName);
    }
  }

  // Render correct Lucide icon based on profile name/meta
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
</script>

<div class="flex flex-col gap-3 mt-2">
  <!-- Top Navigation & Global Settings row -->
  <div class="flex justify-between items-center mb-2 px-1">
    <div class="flex gap-2">
      <button 
        class="btn btn-sm btn-outline gap-1.5 font-bold"
        onclick={() => {
          activeProfileTab = 'list';
          isProfilesModalOpen = true;
        }}
      >
        <Settings size={14} /> Profiles Manager
      </button>
    </div>
    <button class="btn btn-sm btn-primary gap-1.5 font-bold" onclick={triggerCreateDraft}>
      <Plus size={14} /> Add ZRAM Device
    </button>
  </div>

  <!-- Layout: 3-Zone fixed-height container -->
  <div class="grid grid-cols-1 lg:grid-cols-5 gap-4 h-[480px] overflow-hidden">
    
    <!-- Sidebar: Devices (2/5) -->
    <div class="lg:col-span-2 flex flex-col gap-2 overflow-y-auto pr-1 h-full max-h-full scrollbar-thin">
      {#if devices.length === 0}
        <div class="py-12 flex flex-col items-center justify-center text-center w-full bg-base-200/20 border border-base-content/5 rounded-2xl h-full">
          <Info size={28} class="mb-2 opacity-50 text-base-content/40" />
          <p class="text-xs text-base-content/60 font-semibold">No active ZRAM devices.</p>
        </div>
      {:else}
        {#each devices as dev}
          {@const isDirty = dirtyFields[dev.name] && Object.values(dirtyFields[dev.name]).some(v => v === true)}
          <button 
            class="card bg-base-100 border-2 transition-all text-left {selectedDeviceName === dev.name ? 'border-primary' : 'border-base-content/10 hover:border-primary/30'} flex-shrink-0"
            onclick={() => selectDevice(dev.name)}
          >
            <div class="card-body p-3.5 flex flex-col gap-1.5">
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-1.5">
                  <Cpu class={selectedDeviceName === dev.name ? 'text-primary' : 'text-base-content/50'} size={15} />
                  <span class="font-mono font-bold text-sm">{dev.name}</span>
                  {#if dev.isDraft}
                    <span class="badge badge-success badge-xs font-semibold py-1">Draft</span>
                  {:else}
                    <span class="badge badge-neutral badge-xs font-semibold py-1">{dev.algo || 'zstd'}</span>
                  {/if}
                  {#if isDirty}
                    <span class="badge badge-warning badge-xs font-semibold py-1">Unsaved</span>
                  {/if}
                </div>
                <span class="text-[10px] font-mono text-base-content/50 font-bold">{formatBytesToSizeString(dev.totalBytes)}</span>
              </div>
              
              <!-- Snake-Style Arc Gauge Placeholder: compact progress bar -->
              <div class="flex flex-col gap-1">
                <div class="flex justify-between text-[10px] font-mono text-base-content/40">
                  <span>Usage: {formatBytesToSizeString(dev.origBytes)} / {formatBytesToSizeString(dev.totalBytes)}</span>
                  <span>{dev.totalBytes ? Math.round((dev.origBytes / dev.totalBytes) * 100) : 0}%</span>
                </div>
                <progress class="progress progress-primary h-1.5 w-full bg-base-300" value={dev.origBytes || 0} max={dev.totalBytes || 1}></progress>
              </div>
            </div>
          </button>
        {/each}
      {/if}
    </div>

    <!-- Inspector Detail Pane (3/5) -->
    <div class="lg:col-span-3 card bg-base-100 border border-base-content/10 shadow-sm overflow-hidden flex flex-col h-full">
      {#if selectedDeviceName && forms[selectedDeviceName]}
        {@const form = forms[selectedDeviceName]}
        {@const dev = devices.find((d: any) => d.name === selectedDeviceName) || {}}
        <div class="flex flex-col h-full relative">
          {#if form.loading}
            <div class="absolute inset-0 bg-base-100/50 rounded-2xl flex items-center justify-center z-10">
              <Loader2 class="animate-spin text-primary" size={24} />
            </div>
          {/if}

          <!-- Inspector Header -->
          <div class="p-4 border-b border-base-content/5 flex justify-between items-center gap-4 bg-base-200/10">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-mono text-base font-black text-primary">{selectedDeviceName}</h3>
                {#if dev.isDraft}
                  <span class="badge badge-success badge-xs font-semibold py-1">New Device</span>
                {/if}
              </div>
              <p class="text-[10px] text-base-content/50">Custom hardware parameters</p>
            </div>
            
            <div class="flex items-center gap-2">
              <Select 
                value=""
                items={profileItems}
                onchange={handleProfileSelect}
              />
              <button 
                class="btn btn-xs btn-neutral btn-soft font-bold" 
                onclick={() => revertChanges(selectedDeviceName!)}
                disabled={!isCurrentDeviceDirty()}
              >
                Reset
              </button>
              {#if !dev.isDraft}
                <button class="btn btn-xs btn-error btn-soft font-bold" onclick={() => removeZramDevice(selectedDeviceName!)}>
                  Remove
                </button>
              {/if}
            </div>
          </div>

          <!-- Tab Selector Bar -->
          <div class="tabs tabs-box bg-base-200/50 p-1 rounded-none flex border-b border-base-content/5">
            <button 
              class="tab flex-1 text-xs font-bold py-1.5 {activeInspectorTab === 'alloc' ? 'tab-active' : ''}" 
              onclick={() => activeInspectorTab = 'alloc'}
            >
              Allocation
            </button>
            <button 
              class="tab flex-1 text-xs font-bold py-1.5 {activeInspectorTab === 'perf' ? 'tab-active' : ''}" 
              onclick={() => activeInspectorTab = 'perf'}
            >
              Performance
            </button>
            <button 
              class="tab flex-1 text-xs font-bold py-1.5 {activeInspectorTab === 'mount' ? 'tab-active' : ''}" 
              onclick={() => activeInspectorTab = 'mount'}
            >
              Mount & FS
            </button>
          </div>

          <!-- Form Content Area -->
          <div class="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
            {#if activeInspectorTab === 'alloc'}
              <div class="space-y-3 animate-fade-in">
                <div class="grid grid-cols-2 gap-4">
                  <label class="form-control w-full">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Compression Algorithm</span>
                    <Select 
                      bind:value={form.algo}
                      onchange={() => markDirty('algo')}
                      items={[
                        { value: 'zstd', label: 'zstd (Recommended)' },
                        { value: 'lz4', label: 'lz4 (Fastest)' },
                        { value: 'lzo', label: 'lzo' },
                        { value: 'deflate', label: 'deflate' }
                      ]}
                    />
                  </label>
                  <label class="form-control w-full">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Disk Size</span>
                    <input 
                      type="text" 
                      class="input input-xs input-bordered w-full font-mono font-bold" 
                      placeholder="e.g. 4G" 
                      bind:value={form.size} 
                      oninput={() => markDirty('size')}
                    />
                  </label>
                </div>
                <label class="form-control w-full">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Host Memory Limit</span>
                  <input 
                    type="text" 
                    class="input input-xs input-bordered w-full font-mono font-bold" 
                    placeholder="none" 
                    bind:value={form.hostMemLimit} 
                    oninput={() => markDirty('hostMemLimit')}
                  />
                  <span class="text-[10px] text-base-content/40 mt-1">Optional hard limit on physical RAM usage (e.g. 2G or 2048M).</span>
                </label>
              </div>
            {/if}

            {#if activeInspectorTab === 'perf'}
              <div class="space-y-3 animate-fade-in">
                <label class="form-control w-full">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Writeback Backing Device</span>
                  <Select 
                    bind:value={form.backingDev}
                    onchange={() => markDirty('backingDev')}
                    items={blockDeviceItems}
                  />
                </label>
                
                <label class="form-control w-full">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Swap Priority</span>
                  <div class="join w-full">
                    <button 
                      type="button"
                      class="btn btn-xs join-item btn-neutral font-black" 
                      onclick={() => { form.swapPriority = Math.max(-1000, Number(form.swapPriority || 0) - 10); markDirty('swapPriority'); }}
                    >
                      -
                    </button>
                    <input 
                      type="text" 
                      class="input input-xs join-item input-bordered w-full text-center font-mono font-bold" 
                      bind:value={form.swapPriority} 
                      oninput={() => markDirty('swapPriority')}
                    />
                    <button 
                      type="button"
                      class="btn btn-xs join-item btn-neutral font-black" 
                      onclick={() => { form.swapPriority = Math.min(1000, Number(form.swapPriority || 0) + 10); markDirty('swapPriority'); }}
                    >
                      +
                    </button>
                  </div>
                </label>
              </div>
            {/if}

            {#if activeInspectorTab === 'mount'}
              <div class="space-y-3 animate-fade-in">
                <label class="form-control w-full">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Filesystem Type</span>
                  <Select 
                    bind:value={form.fsType}
                    onchange={() => markDirty('fsType')}
                    items={[
                      { value: 'swap', label: 'swap (Default)' },
                      { value: 'ext4', label: 'ext4' },
                      { value: 'ext2', label: 'ext2' },
                      { value: 'tmpfs', label: 'tmpfs' }
                    ]}
                  />
                </label>
                {#if form.fsType && form.fsType !== 'swap'}
                  <label class="form-control w-full">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-base-content/60 mb-1">Mount Point</span>
                    <input 
                      type="text" 
                      class="input input-xs input-bordered w-full font-mono font-bold" 
                      placeholder="e.g. /tmp" 
                      bind:value={form.mountPoint} 
                      oninput={() => markDirty('mountPoint')}
                    />
                  </label>
                {/if}
              </div>
            {/if}
          </div>

          <!-- Sticky Action Footer -->
          <div class="p-3 border-t border-base-content/5 flex justify-between items-center gap-4 bg-base-200/10">
            <div class="flex items-center gap-1.5">
              <button 
                class="btn btn-2xs btn-outline font-bold" 
                onclick={openSaveAsProfile}
                title="Save current parameters to a profile"
              >
                Save as Profile
              </button>
              
              <!-- Apply mode selector -->
              <div class="join border border-base-content/10 rounded-lg overflow-hidden">
                <button 
                  type="button" 
                  class="btn btn-3xs join-item font-semibold px-2 {applyMode === 'both' ? 'btn-neutral' : 'btn-ghost'}" 
                  onclick={() => applyMode = 'both'}
                >
                  Both
                </button>
                <button 
                  type="button" 
                  class="btn btn-3xs join-item font-semibold px-2 {applyMode === 'live' ? 'btn-neutral' : 'btn-ghost'}" 
                  onclick={() => applyMode = 'live'}
                >
                  Live
                </button>
                <button 
                  type="button" 
                  class="btn btn-3xs join-item font-semibold px-2 {applyMode === 'persist' ? 'btn-neutral' : 'btn-ghost'}" 
                  onclick={() => applyMode = 'persist'}
                >
                  Persist
                </button>
              </div>
            </div>
            
            <button 
              class="btn btn-xs btn-primary font-bold gap-1 px-4"
              onclick={() => handleApplyOrSave(selectedDeviceName!)}
            >
              <Save size={12} /> Apply Changes
            </button>
          </div>
        </div>
      {:else}
        <div class="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
          <Cpu size={32} class="mb-2 opacity-30 text-base-content/40" />
          <p class="text-xs text-base-content/60 font-semibold">Select a device from sidebar</p>
        </div>
      {/if}
    </div>

  </div>
</div>

<!-- Profiles Manager Bits UI Dialog -->
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
      <div class="flex-1 overflow-y-auto p-4 scrollbar-thin">
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
                    onclick={() => deleteProfile(name)}
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

            <button 
              class="btn btn-sm btn-primary w-full mt-2 font-bold"
              onclick={createCustomProfile}
              disabled={loadingProfileDialog}
            >
              {#if loadingProfileDialog}<Loader2 class="animate-spin" size={14} />{/if}
              Save Profile Template
            </button>
          </div>
        {/if}
      </div>

    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
