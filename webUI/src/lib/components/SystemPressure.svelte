<script lang="ts">
  import Sparkline from './Sparkline.svelte';
  import { Activity } from 'lucide-svelte';

  let { psi } = $props<{
    psi: any;
  }>();
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-6 flex flex-col gap-6">
  <div class="flex items-center gap-3">
    <Activity class="text-primary" size={22} />
    <div>
      <h2 class="text-lg font-bold">System Pressure</h2>
      <p class="text-xs text-base-content/60">PSI Stall Information · Last 60 seconds</p>
    </div>
  </div>

  <div class="flex flex-col gap-5 bg-base-200/20 p-4 rounded-2xl border border-base-content/5">
    <!-- CPU Pressure -->
    <Sparkline 
      value={psi?.cpu?.some ?? 0} 
      label="CPU Stall (Some)" 
      colorClass="stroke-secondary"
    />

    <!-- Memory Pressure -->
    <Sparkline 
      value={psi?.memory?.some ?? 0} 
      label="Memory Stall (Some)" 
      colorClass={psi?.memory?.some > 15 ? 'stroke-warning' : 'stroke-primary'}
    />

    <!-- I/O Pressure -->
    <Sparkline 
      value={psi?.io?.some ?? 0} 
      label="I/O Stall (Some)" 
      colorClass="stroke-accent"
    />
  </div>
</div>
