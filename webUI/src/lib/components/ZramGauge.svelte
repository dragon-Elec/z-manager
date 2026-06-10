<script lang="ts">
  import { Settings, HardDrive, Info } from 'lucide-svelte';

  let {
    name = 'zram0',
    algo = 'zstd',
    usedBytes = 0,
    totalBytes = 0,
    origBytes = 0,
    comprBytes = 0,
    ramTotal = 1,
    isSwap = true,
    backingDev = '',
    bdUsed = 0,
    bdLimit = 0,
    memUsedTotalBytes = 0,
    wbNum = 0,
    wbFailed = 0,
    onclick = () => {},
    onconfigure = () => {}
  } = $props<{
    name?: string;
    algo?: string;
    usedBytes?: number;
    totalBytes?: number;
    origBytes?: number;
    comprBytes?: number;
    ramTotal?: number;
    isSwap?: boolean;
    backingDev?: string | null;
    bdUsed?: number;
    bdLimit?: number;
    memUsedTotalBytes?: number;
    wbNum?: number;
    wbFailed?: number;
    onclick?: () => void;
    onconfigure?: () => void;
  }>();

  // Helper to format bytes to human readable exactly like _format_size in Cairo
  function formatSize(size: number) {
    let s = size;
    for (const unit of ['B', 'KiB', 'MiB', 'GiB', 'TiB']) {
      if (Math.abs(s) < 1024.0) {
        return `${s.toFixed(1)} ${unit}`;
      }
      s /= 1024.0;
    }
    return `${s.toFixed(1)} PiB`;
  }

  // Helper to format writeback size without spaces
  function formatSizeCompact(size: number) {
    return formatSize(size).replace(/\s+/g, '');
  }

  let efficiency = $derived(comprBytes > 0 ? (origBytes / comprBytes) : 1.0);
  let usagePct = $derived(totalBytes > 0 ? (usedBytes / totalBytes) * 100 : 0);

  // SVG Circle Math (Strict Proportions for 156x158 area)
  const size = 156;
  const radius = 70.2; // (156 / 2) - 156 * 0.05 = 78 - 7.8 = 70.2
  const lineWidth = 9.36; // 156 * 0.06 = 9.36
  const circumference = 2 * Math.PI * radius; // ~441.07
  
  // Arcs based on physical RAM limit
  let limit = $derived(ramTotal > 0 ? ramTotal : 1);
  let solidPct = $derived(Math.min((comprBytes / limit) * 100, 100));
  let ghostPct = $derived(Math.min((origBytes / limit) * 100, 100));
  
  let solidDash = $derived((solidPct / 100) * circumference);
  let ghostDash = $derived((ghostPct / 100) * circumference);

  // Danger state: original uncompressed data exceeds RAM limit
  let isDanger = $derived(origBytes >= limit);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div 
  class="card-widget bg-base-200/40 border border-base-content/5 shadow-sm flex flex-col items-center select-none relative hover:border-primary/30 hover:shadow-md transition-all duration-150 cursor-pointer"
  onclick={onclick}
>
  
  <!-- Writeback Icon + Stats (Top Left) -->
  {#if backingDev && backingDev !== 'none' && backingDev !== 'None Selected' && backingDev !== 'none selected'}
    <div 
      class="absolute top-2 left-2 flex items-center gap-1 text-[10px] font-condensed text-base-content/60 bg-base-300/40 px-1.5 py-0.5 rounded-md border border-base-content/5"
      title="Writeback: {backingDev} ({wbNum} pages written)"
    >
      <HardDrive size={11} class="opacity-60" />
      <span>{formatSizeCompact(wbNum * 4096)}</span>
    </div>
  {/if}

  <!-- Configure Icon (Top Right) -->
  <button 
    class="absolute top-2 right-2 text-base-content/40 hover:text-primary transition-colors focus:outline-none z-10"
    title="Configure Device"
    onclick={(e) => {
      e.stopPropagation();
      onconfigure();
    }}
  >
    <Settings size={20} />
  </button>

  <!-- Circular Gauge (Exact 156x170 Drawing Area) -->
  <div class="w-[156px] h-[170px] mt-[12px] relative">
    <svg class="w-full h-full" viewBox="0 0 156 170">
      <!-- Rotated Group: So stroke starts at Left (9 o'clock) and runs clockwise -->
      <g class="origin-center -rotate-180">
        <!-- Background Track -->
        <circle 
          cx="78" 
          cy="85" 
          r={radius} 
          fill="none" 
          class="stroke-base-content/10" 
          stroke-width={lineWidth} 
          stroke-linecap="round" 
        />
        
        <!-- Ghost Arc (Original Size) -->
        <circle 
          cx="78" 
          cy="85" 
          r={radius} 
          fill="none" 
          class={isDanger ? "stroke-error/30" : "stroke-primary/20"} 
          stroke-width={lineWidth} 
          stroke-linecap="round"
          stroke-dasharray="{isDanger ? circumference : ghostDash} {circumference}" 
        />
                
        <!-- Solid Arc (Compressed Size) -->
        <circle 
          cx="78" 
          cy="85" 
          r={radius} 
          fill="none" 
          class="stroke-primary" 
          stroke-width={lineWidth} 
          stroke-linecap="round"
          stroke-dasharray="{solidDash} {circumference}" 
        />
      </g>

      <!-- Center Text elements (rendered at precise Cairo offsets relative to cy=85) -->
      <text 
        x="78" 
        y="77" 
        text-anchor="middle" 
        class="fill-base-content font-bold text-[27px]"
      >
        {name}
      </text>

      <text 
        x="78" 
        y="91" 
        text-anchor="middle" 
        class="fill-base-content font-mono text-[13px] tracking-wide"
      >
        {isSwap ? '[SWAP]' : '[ZRAM]'}
      </text>

      <text 
        x="78" 
        y="105" 
        text-anchor="middle" 
        class="fill-base-content/60 font-mono text-[13px]"
      >
        {algo}
      </text>

      <text 
        x="78" 
        y="128" 
        text-anchor="middle" 
        class="fill-base-content font-bold text-[20px]"
      >
        {efficiency.toFixed(1)}x
      </text>
    </svg>
  </div>

  <!-- Bottom Usage Area (Tight 2px spacing) -->
  <div class="w-[156px] mb-[12px] flex flex-col gap-[2px]">
    <div class="text-[12px] font-condensed font-light text-base-content/85 leading-none text-center">
      {formatSize(usedBytes)} / {formatSize(totalBytes)}
    </div>
    
    <div class="flex items-center gap-2 w-full">
      <progress 
        class="progress progress-primary flex-1 h-2 bg-base-content/10 rounded-md" 
        value={usagePct} 
        max="100"
      ></progress>
      <span class="text-[12px] font-condensed font-light text-base-content/90 whitespace-nowrap leading-none">
        {Math.round(usagePct)}%
      </span>
    </div>
  </div>

</div>

<style>
  .card-widget {
    width: 180px;
    height: 220px;
    border-radius: 1.5rem;
  }

  .font-condensed {
    font-family: "Roboto Condensed", "DIN Alternate", "Arial Narrow", sans-serif;
    font-stretch: condensed;
    font-weight: 300;
  }
</style>