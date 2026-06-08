<script lang="ts">
  import { untrack } from 'svelte';

  let { value = 0, label = "", colorClass = "stroke-primary" } = $props<{
    value: number;
    label: string;
    colorClass?: string;
  }>();

  let history = $state<number[]>([]);

  // Push new value to history and keep last 60 points (60 seconds)
  $effect(() => {
    const currentVal = value;
    untrack(() => {
      history = [...history, currentVal].slice(-60);
    });
  });

  // Convert history points to SVG path coordinates
  let pathData = $derived.by(() => {
    if (history.length === 0) return "";
    const width = 200;
    const height = 40;
    // Find the maximum value in history to scale the y-axis, but cap minimum scale at 5.0
    const maxVal = Math.max(5.0, ...history);
    const points = history.map((val, index) => {
      const x = (index / (history.length - 1 || 1)) * width;
      const y = height - (val / maxVal) * (height - 6) - 3; // 3px padding top/bottom
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return `M ${points.join(" L ")}`;
  });
</script>

<div class="flex items-center justify-between gap-4 w-full">
  <div class="flex flex-col">
    <span class="text-xs uppercase tracking-wider text-base-content/50 font-semibold">{label}</span>
    <span class="text-xl font-mono font-bold">{value.toFixed(2)}%</span>
  </div>
  
  <div class="flex-1 max-w-[200px] h-[40px] relative">
    {#if history.length > 1}
      <svg class="w-full h-full overflow-visible" viewBox="0 0 200 40">
        <!-- Area fill under sparkline -->
        <path
          d="{pathData} L 200,40 L 0,40 Z"
          class="fill-current opacity-10 {colorClass.replace('stroke-', 'text-')}"
        />
        <!-- Sparkline stroke -->
        <path
          d={pathData}
          fill="none"
          class="stroke-[2px] {colorClass}"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    {:else}
      <div class="w-full h-full flex items-center justify-center text-xs text-base-content/30 italic">
        Gathering...
      </div>
    {/if}
  </div>
</div>
