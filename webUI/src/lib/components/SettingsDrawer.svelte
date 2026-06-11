<script lang="ts">
  import { Dialog } from 'bits-ui';
  import { Settings } from 'lucide-svelte';
  import Select from './Select.svelte';

  let {
    open = $bindable(false),
    themeMode = $bindable('system'),
    availableThemes,
    backendConnected,
    onChangeTheme
  } = $props<{
    open: boolean;
    themeMode: string;
    availableThemes: string[];
    backendConnected: boolean;
    onChangeTheme: (mode: string) => void;
  }>();

  // Map themes to Select items format
  let themeItems = $derived.by(() => {
    const items = [
      { value: 'system', label: 'System (Auto)' },
      { value: 'light', label: 'Light (Nord)' },
      { value: 'dark', label: 'Dark (Nord-Dark)' }
    ];
    
    availableThemes.forEach(theme => {
      if (theme !== 'light' && theme !== 'dark' && theme !== 'nord' && theme !== 'nord-dark') {
        items.push({
          value: theme,
          label: theme.charAt(0).toUpperCase() + theme.slice(1)
        });
      }
    });
    
    return items;
  });
</script>

<Dialog.Root bind:open={open}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <Dialog.Content class="fixed right-0 top-0 bottom-0 z-50 w-80 border-l border-base-content/10 bg-base-100/90 backdrop-blur-md p-6 shadow-lg outline-none flex flex-col justify-between">
      <div>
        <Dialog.Title class="text-xl font-bold flex items-center gap-2 mb-6">
          <Settings size={20} /> Settings
        </Dialog.Title>
        
        <div class="space-y-6">
          <!-- Connection Status -->
          <div class="flex flex-col gap-2">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Backend Connection</span>
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full {backendConnected ? 'bg-primary' : 'bg-error'}"></span>
              <span class="text-sm font-medium">{backendConnected ? 'Connected (Native)' : 'Disconnected'}</span>
            </div>
          </div>

          <!-- Theme Override -->
          <div class="flex flex-col gap-2">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Theme Mode</span>
            <Select 
              bind:value={themeMode}
              items={themeItems}
              onchange={onChangeTheme}
            />
          </div>

          <!-- App Version -->
          <div class="flex flex-col gap-1">
            <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">Version</span>
            <span class="text-sm font-mono text-base-content/80">v0.9.0-beta</span>
          </div>
        </div>
      </div>
      
      <Dialog.Close class="btn btn-soft w-full mt-6">Close</Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
