<script lang="ts">
  import { Select } from 'bits-ui';
  import { ChevronDown, Check } from 'lucide-svelte';

  let {
    value = $bindable(),
    items,
    placeholder = 'Select...',
    disabled = false,
    onchange
  } = $props<{
    value: string;
    items: { value: string; label: string }[];
    placeholder?: string;
    disabled?: boolean;
    onchange?: (val: string) => void;
  }>();

  let selectedLabel = $derived(
    items.find((item) => item.value === value)?.label ?? placeholder
  );

  function handleValueChange(val: string) {
    value = val;
    if (onchange) {
      onchange(val);
    }
  }
</script>

<Select.Root type="single" bind:value onValueChange={handleValueChange} disabled={disabled}>
  <Select.Trigger class="btn btn-sm btn-outline justify-between w-full font-medium">
    <span class="truncate">{selectedLabel}</span>
    <ChevronDown size={14} class="opacity-60 shrink-0" />
  </Select.Trigger>
  <Select.Portal>
    <Select.Content class="z-50 min-w-[12rem] max-h-60 overflow-y-auto rounded-xl border border-base-content/10 bg-base-200 p-1 shadow-lg flex flex-col gap-0.5">
      {#each items as item}
        <Select.Item
          value={item.value}
          label={item.label}
          class="flex w-full cursor-default select-none items-center rounded-lg px-3 py-2 text-sm outline-none hover:bg-base-300 focus:bg-base-300 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 font-medium justify-between"
        >
          {#snippet children({ selected })}
            <span>{item.label}</span>
            {#if selected}
              <Check size={14} class="text-primary shrink-0" />
            {/if}
          {/snippet}
        </Select.Item>
      {/each}
    </Select.Content>
  </Select.Portal>
</Select.Root>
