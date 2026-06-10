<script lang="ts">
  import { Dialog } from 'bits-ui';
  import { AlertTriangle } from 'lucide-svelte';

  let {
    open = $bindable(false),
    title,
    desc,
    onConfirm
  } = $props<{
    open: boolean;
    title: string;
    desc: string;
    onConfirm: () => void;
  }>();
</script>

<Dialog.Root bind:open={open}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <Dialog.Content class="w-full max-w-md rounded-2xl border border-base-content/10 bg-base-100/95 backdrop-blur-md p-6 shadow-lg outline-none">
        <Dialog.Title class="text-lg font-bold flex items-center gap-2 text-warning">
          <AlertTriangle size={20} /> {title}
        </Dialog.Title>
        <Dialog.Description class="mt-2 text-sm text-base-content/70">
          {desc}
        </Dialog.Description>
        <div class="mt-6 flex justify-end gap-3">
          <Dialog.Close class="btn btn-soft">Cancel</Dialog.Close>
          <button class="btn btn-warning" onclick={onConfirm}>Confirm</button>
        </div>
      </Dialog.Content>
    </div>
  </Dialog.Portal>
</Dialog.Root>