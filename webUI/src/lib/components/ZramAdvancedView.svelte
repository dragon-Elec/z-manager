<script lang="ts">
  import { 
    Cpu, Plus, Settings, SlidersHorizontal, Info, Play, Save, X, Trash2, 
    RefreshCw, Loader2, Gamepad2, Scale, Server, Box, Battery, Shield, Database,
    HardDrive, Zap, Activity, Terminal
  } from 'lucide-svelte';
  import { Dialog } from 'bits-ui';
  import Select from './Select.svelte';
  import ZramProfilesModal from './ZramProfilesModal.svelte';

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
    sizeMode: string;
    size: string;
    backingDev: string;
    swapPriority: number;
    hostMemLimit: string;
    residentLimit: string;
    options: string;
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
  $effect(() => {
    if (devices) {
      devices.forEach((dev: any) => {
        if (!forms[dev.name]) {
          forms[dev.name] = {
            algo: dev.algo || 'zstd',
            sizeMode: 'custom',
            size: formatBytesToSizeString(dev.totalBytes) || '2G',
            backingDev: dev.backingDev || 'none',
            swapPriority: dev.swapPriority !== undefined ? dev.swapPriority : 100,
            hostMemLimit: dev.hostMemLimit || '',
            residentLimit: dev.residentLimit || '',
            options: dev.options || '',
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
          if (!dirty.residentLimit && !form.loading) form.residentLimit = dev.residentLimit || '';
          if (!dirty.options && !form.loading) form.options = dev.options || '';
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
      form.residentLimit = dev.residentLimit || '';
      form.options = dev.options || '';
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
        residentLimit: form.residentLimit || null,
        options: form.options || null,
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
      sizeMode: 'custom',
      size: '2G',
      backingDev: 'none',
      swapPriority: 100,
      hostMemLimit: '',
      residentLimit: '',
      options: '',
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
          residentLimit: form.residentLimit || null,
          options: form.options || null,
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
  export function openProfilesManager() {
    activeProfileTab = 'list';
    isProfilesModalOpen = true;
  }

  export function addZramDevice() {
    triggerCreateDraft();
  }
</script>

<div class="flex flex-col gap-3 mt-2">
  <!-- Layout: 3-Zone fixed-height container -->
  <div class="flex h-[550px] overflow-hidden border border-base-content/10 rounded-xl bg-base-100">
    
    <!-- Sidebar: Devices -->
    <div class="w-72 flex-shrink-0 flex flex-col gap-2 overflow-y-auto p-3 border-r border-base-content/10 bg-base-200/20 scrollbar-thin">
      {#if devices.length === 0}
        <div class="py-12 flex flex-col items-center justify-center text-center w-full h-full">
          <Info size={28} class="mb-2 opacity-50 text-base-content/40" />
          <p class="text-xs text-base-content/60 font-semibold">No active ZRAM devices.</p>
        </div>
      {:else}
        {#each devices as dev}
          {@const isDirty = dirtyFields[dev.name] && Object.values(dirtyFields[dev.name]).some(v => v === true)}
          <button 
            class="card bg-base-100 border transition-all text-left {selectedDeviceName === dev.name ? 'border-primary shadow-sm' : 'border-base-content/10 hover:border-primary/30'} flex-shrink-0"
            onclick={() => selectDevice(dev.name)}
          >
            <div class="card-body p-3 flex flex-col gap-2">
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
              
              <!-- Thick Progress Bar -->
              <div class="flex flex-col gap-1">
                <div class="flex justify-between text-[10px] font-mono text-base-content/40">
                  <span>Usage: {formatBytesToSizeString(dev.origBytes)} / {formatBytesToSizeString(dev.totalBytes)}</span>
                  <span>{dev.totalBytes ? Math.round((dev.origBytes / dev.totalBytes) * 100) : 0}%</span>
                </div>
                <div class="h-2 rounded-full bg-base-300 overflow-hidden w-full">
                  <div class="h-full bg-primary" style="width: {dev.totalBytes ? Math.round((dev.origBytes / dev.totalBytes) * 100) : 0}%"></div>
                </div>
              </div>
            </div>
          </button>
        {/each}
      {/if}
    </div>

    <!-- Inspector Detail Pane -->
    <div class="flex-1 flex flex-col relative bg-base-100 overflow-hidden">
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
          <div class="p-6 pb-4 flex justify-between items-end max-w-4xl mx-auto w-full">
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-2xl font-bold font-mono text-primary">{selectedDeviceName}</h2>
                {#if dev.isDraft}
                  <span class="badge badge-success badge-xs font-semibold py-1">New Device</span>
                {/if}
              </div>
              <p class="text-sm text-base-content/60">Custom hardware parameters</p>
            </div>
            
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold uppercase tracking-wider text-base-content/60">Apply Profile:</span>
              <div class="w-48">
                <Select 
                  value=""
                  items={profileItems}
                  onchange={handleProfileSelect}
                />
              </div>
              <button 
                class="btn btn-sm btn-neutral btn-soft font-bold" 
                onclick={() => revertChanges(selectedDeviceName!)}
                disabled={!isCurrentDeviceDirty()}
                title="Revert Changes"
              >
                <RefreshCw size={14} />
              </button>
              {#if !dev.isDraft}
                <button class="btn btn-sm btn-error btn-soft font-bold" onclick={() => removeZramDevice(selectedDeviceName!)} title="Remove Device">
                  <Trash2 size={14} />
                </button>
              {/if}
            </div>
          </div>

          <!-- Tab Selector Bar -->
          <div class="px-6 max-w-4xl mx-auto w-full mb-6">
            <div class="flex bg-base-200/50 p-1 rounded-lg border border-base-content/10">
              <button 
                class="flex-1 text-center py-1.5 text-sm font-bold rounded-md transition-all {activeInspectorTab === 'alloc' ? 'bg-base-100 text-base-content shadow-sm' : 'text-base-content/60 hover:text-base-content'}" 
                onclick={() => activeInspectorTab = 'alloc'}
              >
                Allocation
              </button>
              <button 
                class="flex-1 text-center py-1.5 text-sm font-bold rounded-md transition-all {activeInspectorTab === 'perf' ? 'bg-base-100 text-base-content shadow-sm' : 'text-base-content/60 hover:text-base-content'}" 
                onclick={() => activeInspectorTab = 'perf'}
              >
                Performance
              </button>
              <button 
                class="flex-1 text-center py-1.5 text-sm font-bold rounded-md transition-all {activeInspectorTab === 'mount' ? 'bg-base-100 text-base-content shadow-sm' : 'text-base-content/60 hover:text-base-content'}" 
                onclick={() => activeInspectorTab = 'mount'}
              >
                Mount & FS
              </button>
            </div>
          </div>

          <!-- Form Content Area -->
          <div class="flex-1 overflow-y-auto px-6 pb-24 max-w-4xl mx-auto w-full scrollbar-thin">
            {#if activeInspectorTab === 'alloc'}
              <div class="animate-fade-in bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden">
                <!-- Row 1 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Compression Algorithm</span>
                    <span class="text-xs text-base-content/60">Determines compression speed vs ratio.</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
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
                  </div>
                </div>
                <!-- Row 2 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">ZRAM Block Size</span>
                    <span class="text-xs text-base-content/60">Virtual uncompressed size of the block device.</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <Select 
                      bind:value={form.sizeMode}
                      onchange={(val) => {
                        if (val === 'half') form.size = 'ram / 2';
                        else if (val === 'full') form.size = 'ram';
                        markDirty('size');
                      }}
                      items={[
                        { value: 'half', label: '50% of RAM' },
                        { value: 'full', label: '100% of RAM' },
                        { value: 'custom', label: 'Custom' }
                      ]}
                    />
                  </div>
                </div>

                {#if form.sizeMode === 'custom'}
                  <!-- Row 2.5 (Custom Size) -->
                  <div class="flex justify-between items-center p-4 border-b border-base-content/10 bg-base-200/10">
                    <div class="flex flex-col gap-1">
                      <span class="text-sm font-bold">Custom Size</span>
                      <span class="text-xs text-base-content/60">e.g. 8G, 2048M, or min(ram / 2, 4096)</span>
                    </div>
                    <div class="w-56 flex-shrink-0">
                      <input 
                        type="text" 
                        class="input input-sm input-bordered w-full font-mono font-bold" 
                        placeholder="e.g. 4G" 
                        bind:value={form.size} 
                        oninput={() => markDirty('size')}
                      />
                    </div>
                  </div>
                {/if}

                <!-- Row 3 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Host Memory Limit</span>
                    <span class="text-xs text-base-content/60">Only enable if host has enough RAM (e.g. 2048M).</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <input 
                      type="text" 
                      class="input input-sm input-bordered w-full font-mono font-bold" 
                      placeholder="none" 
                      bind:value={form.hostMemLimit} 
                      oninput={() => markDirty('hostMemLimit')}
                    />
                  </div>
                </div>

                <!-- Row 4 -->
                <div class="flex justify-between items-center p-4">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Resident Memory Limit</span>
                    <span class="text-xs text-base-content/60">Hard cap on physical RAM usage (e.g. 2G).</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <input 
                      type="text" 
                      class="input input-sm input-bordered w-full font-mono font-bold" 
                      placeholder="none" 
                      bind:value={form.residentLimit} 
                      oninput={() => markDirty('residentLimit')}
                    />
                  </div>
                </div>
              </div>
            {/if}

            {#if activeInspectorTab === 'perf'}
              <div class="animate-fade-in bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden">
                <!-- Row 1 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Writeback Backing Device</span>
                    <span class="text-xs text-base-content/60">Physical partition for incompressible pages.</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <Select 
                      bind:value={form.backingDev}
                      onchange={() => markDirty('backingDev')}
                      items={blockDeviceItems}
                    />
                  </div>
                </div>
                
                <!-- Row 2 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Swap Priority</span>
                    <span class="text-xs text-base-content/60">Kernel swap priority (-1000 to 1000).</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <div class="join w-full">
                      <button 
                        type="button"
                        class="btn btn-sm join-item btn-neutral font-black" 
                        onclick={() => { form.swapPriority = Math.max(-1000, Number(form.swapPriority || 0) - 10); markDirty('swapPriority'); }}
                      >
                        -
                      </button>
                      <input 
                        type="text" 
                        class="input input-sm join-item input-bordered w-full text-center font-mono font-bold" 
                        bind:value={form.swapPriority} 
                        oninput={() => markDirty('swapPriority')}
                      />
                      <button 
                        type="button"
                        class="btn btn-sm join-item btn-neutral font-black" 
                        onclick={() => { form.swapPriority = Math.min(1000, Number(form.swapPriority || 0) + 10); markDirty('swapPriority'); }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Row 3 -->
                <div class="flex justify-between items-center p-4">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Extra Options</span>
                    <span class="text-xs text-base-content/60">Additional zram-generator options.</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
                    <input 
                      type="text" 
                      class="input input-sm input-bordered w-full font-mono font-bold" 
                      placeholder="e.g. writeback-disable" 
                      bind:value={form.options} 
                      oninput={() => markDirty('options')}
                    />
                  </div>
                </div>
              </div>
            {/if}

            {#if activeInspectorTab === 'mount'}
              <div class="animate-fade-in bg-base-200/30 border border-base-content/10 rounded-xl overflow-hidden">
                <!-- Row 1 -->
                <div class="flex justify-between items-center p-4 border-b border-base-content/10">
                  <div class="flex flex-col gap-1">
                    <span class="text-sm font-bold">Filesystem Type</span>
                    <span class="text-xs text-base-content/60">Format device as swap or standard FS.</span>
                  </div>
                  <div class="w-56 flex-shrink-0">
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
                  </div>
                </div>
                
                {#if form.fsType && form.fsType !== 'swap'}
                  <!-- Row 2 -->
                  <div class="flex justify-between items-center p-4">
                    <div class="flex flex-col gap-1">
                      <span class="text-sm font-bold">Mount Point</span>
                      <span class="text-xs text-base-content/60">Absolute path to mount the filesystem.</span>
                    </div>
                    <div class="w-56 flex-shrink-0">
                      <input 
                        type="text" 
                        class="input input-sm input-bordered w-full font-mono font-bold" 
                        placeholder="e.g. /tmp" 
                        bind:value={form.mountPoint} 
                        oninput={() => markDirty('mountPoint')}
                      />
                    </div>
                  </div>
                {/if}
              </div>
            {/if}
          </div>

          <!-- Sticky Action Footer -->
          <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-base-content/10 flex justify-between items-center gap-4 bg-base-100/90 backdrop-blur z-10">
            <button 
              class="btn btn-sm btn-ghost text-error hover:bg-error/20 font-bold" 
              onclick={() => revertChanges(selectedDeviceName!)}
              disabled={!isCurrentDeviceDirty()}
            >
              <RefreshCw size={14} /> Revert
            </button>
            
            <div class="flex items-center gap-0 rounded-lg overflow-hidden border border-base-content/10">
              <div class="flex bg-base-300 text-xs font-bold">
                <button 
                  type="button" 
                  class="px-3 py-1.5 transition-colors {applyMode === 'both' ? 'bg-base-content text-base-100' : 'hover:bg-base-200'}" 
                  onclick={() => applyMode = 'both'}
                >
                  Both
                </button>
                <button 
                  type="button" 
                  class="px-3 py-1.5 transition-colors {applyMode === 'live' ? 'bg-base-content text-base-100' : 'hover:bg-base-200'}" 
                  onclick={() => applyMode = 'live'}
                >
                  Live
                </button>
                <button 
                  type="button" 
                  class="px-3 py-1.5 transition-colors {applyMode === 'persist' ? 'bg-base-content text-base-100' : 'hover:bg-base-200'}" 
                  onclick={() => applyMode = 'persist'}
                >
                  Persist
                </button>
              </div>
              <button 
                class="px-4 py-1.5 font-bold flex items-center gap-2 bg-primary text-primary-content hover:bg-primary/90 transition-colors"
                onclick={() => handleApplyOrSave(selectedDeviceName!)}
              >
                <Save size={14} /> Apply Changes
              </button>
            </div>
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
<ZramProfilesModal 
  bind:isProfilesModalOpen
  {availableProfiles}
  {addCustomProfile}
  {deleteProfile}
  {showToast}
/>
