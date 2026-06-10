<script lang="ts">
  import { Dialog, DropdownMenu } from 'bits-ui';
  import { Settings, ChevronDown } from 'lucide-svelte';

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
            
            <DropdownMenu.Root>
              <DropdownMenu.Trigger class="btn btn-sm btn-outline justify-between w-full font-medium">
                <span class="truncate">{themeMode === 'system' ? 'System (Auto)' : themeMode.charAt(0).toUpperCase() + themeMode.slice(1)}</span>
                <ChevronDown size={14} class="opacity-60 shrink-0" />
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content class="z-50 min-w-[12rem] max-h-60 overflow-y-auto rounded-xl border border-base-content/10 bg-base-200 p-1 shadow-lg flex flex-col gap-0.5">
                  <DropdownMenu.Item 
                    class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium"
                    onclick={() => onChangeTheme('system')}
                  >
                    System (Auto)
                  </DropdownMenu.Item>
                  <DropdownMenu.Separator class="my-1 h-px bg-base-content/10" />
                  {#each availableThemes as theme}
                    <DropdownMenu.Item 
                      class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium"
                      onclick={() => onChangeTheme(theme)}
                    >
                      {theme.charAt(0).toUpperCase() + theme.slice(1)}
                    </DropdownMenu.Item>
                  {/each}
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
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
