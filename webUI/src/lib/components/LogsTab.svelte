<script lang="ts">
  import { onMount } from 'svelte';
  import { Terminal, RefreshCw } from 'lucide-svelte';
  import { sendToPython } from '../bridge';

  let {
    devices = [],
    showToast
  } = $props<{
    devices?: any[];
    showToast: (type: 'success' | 'error' | 'info', message: string) => void;
  }>();

  // State variables
  let selectedUnit = $state("systemd-zram-setup@zram0.service");
  let logCount = $state(50);
  let logs = $state<any[]>([]);
  let filterText = $state("");
  let loading = $state(false);
  let expandedIndex = $state<number | null>(null);

  // Derived unique units list
  let units = $derived([
    ...new Set([
      'systemd-zram-setup@zram0.service',
      ...(devices || []).map(dev => `systemd-zram-setup@${dev.name}.service`).filter(Boolean)
    ])
  ]);

  // Derived filtered logs
  let filteredLogs = $derived(
    logs.filter(log => {
      if (!filterText) return true;
      const term = filterText.toLowerCase();
      return (
        log.message.toLowerCase().includes(term) ||
        (log.timestamp && log.timestamp.toLowerCase().includes(term))
      );
    })
  );

  async function fetchLogs() {
    loading = true;
    expandedIndex = null;
    try {
      const res = await sendToPython("get_journal_logs", {
        unit: selectedUnit,
        count: logCount
      });
      if (res && res.status === "success") {
        logs = res.logs || [];
      } else {
        showToast("error", res?.message || "Failed to load journal logs");
      }
    } catch (e: any) {
      showToast("error", `Error loading journal logs: ${e.message}`);
    } finally {
      loading = false;
    }
  }

  // Format local timestamp
  function formatLocalTime(isoStr: string) {
    try {
      const date = new Date(isoStr);
      if (isNaN(date.getTime())) return isoStr;
      
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    } catch (e) {
      return isoStr;
    }
  }

  // Effect to load when unit or count changes
  $effect(() => {
    // Read the values to trigger the effect
    const u = selectedUnit;
    const c = logCount;
    fetchLogs();
  });

  function toggleExpand(index: number) {
    if (expandedIndex === index) {
      expandedIndex = null;
    } else {
      expandedIndex = index;
    }
  }
</script>

<div class="card bg-base-100 border border-base-content/10 shadow-sm p-4 md:p-6 flex flex-col gap-4">
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-base-content/10 pb-4">
    <div>
      <h2 class="text-xl font-bold flex items-center gap-2">
        <Terminal class="text-primary" size={20} />
        System Journal Logs
      </h2>
      <p class="text-sm text-base-content/60">Inspect systemd service events</p>
    </div>
  </div>

  <!-- Toolbar -->
  <div class="flex flex-wrap items-center gap-3">
    <!-- Unit selector -->
    <div class="flex flex-col gap-1 min-w-[220px]">
      <span class="text-xs font-semibold text-base-content/60">Systemd Unit</span>
      <select 
        class="select select-bordered select-sm w-full font-medium"
        bind:value={selectedUnit}
      >
        {#each units as unit}
          <option value={unit}>{unit}</option>
        {/each}
      </select>
    </div>

    <!-- Log Count selector -->
    <div class="flex flex-col gap-1 w-24">
      <span class="text-xs font-semibold text-base-content/60">Count</span>
      <select 
        class="select select-bordered select-sm w-full font-medium"
        bind:value={logCount}
      >
        <option value={25}>25</option>
        <option value={50}>50</option>
        <option value={100}>100</option>
        <option value={200}>200</option>
      </select>
    </div>

    <!-- Text filter input -->
    <div class="flex flex-col gap-1 flex-1 min-w-[200px]">
      <span class="text-xs font-semibold text-base-content/60">Filter Message</span>
      <input 
        type="text" 
        placeholder="Filter logs by message..." 
        class="input input-bordered input-sm w-full font-medium"
        bind:value={filterText}
      />
    </div>

    <!-- Refresh button -->
    <div class="flex flex-col gap-1 justify-end pt-5">
      <button 
        class="btn btn-sm btn-outline btn-primary" 
        onclick={fetchLogs} 
        disabled={loading}
        aria-label="Refresh Logs"
      >
        <RefreshCw size={14} class={loading ? "animate-spin" : ""} />
        Refresh
      </button>
    </div>
  </div>

  <!-- Logs Table/List -->
  <div class="border border-base-content/10 rounded-xl overflow-hidden bg-base-200">
    {#if loading && logs.length === 0}
      <div class="flex flex-col items-center justify-center p-12 gap-2 text-base-content/60">
        <RefreshCw size={24} class="animate-spin text-primary" />
        <span>Fetching logs...</span>
      </div>
    {:else if filteredLogs.length === 0}
      <div class="flex flex-col items-center justify-center p-12 text-base-content/60">
        <span>No log entries found.</span>
      </div>
    {:else}
      <div class="max-h-[500px] overflow-y-auto font-mono text-xs divide-y divide-base-content/10">
        {#each filteredLogs as log, index}
          {@const formattedTime = formatLocalTime(log.timestamp)}
          <div class="flex flex-col">
            <!-- Log header row (clickable) -->
            <button 
              class="w-full text-left p-2.5 hover:bg-base-300 transition-colors flex items-start gap-2 focus:outline-none"
              onclick={() => toggleExpand(index)}
              aria-expanded={expandedIndex === index}
            >
              <span class="text-base-content/40 shrink-0 select-none">
                [{formattedTime}]
              </span>

              {#if log.priority <= 3}
                <span class="badge badge-error badge-xs font-semibold shrink-0 uppercase">Error</span>
                <span class="text-error font-medium break-all">{log.message}</span>
              {:else if log.priority === 4}
                <span class="badge badge-warning badge-xs font-semibold shrink-0 uppercase text-warning-content">Warn</span>
                <span class="text-warning font-medium break-all">{log.message}</span>
              {:else}
                <span class="badge badge-neutral badge-xs font-semibold shrink-0 uppercase">Info</span>
                <span class="text-base-content break-all">{log.message}</span>
              {/if}
            </button>

            <!-- Expanded Details -->
            {#if expandedIndex === index}
              <div class="p-3 bg-base-300/50 border-t border-base-content/10 overflow-x-auto">
                <span class="text-[10px] font-bold text-base-content/50 uppercase tracking-wider block mb-1">Metadata Fields</span>
                <pre class="text-[10px] text-base-content/80 whitespace-pre-wrap">{JSON.stringify(log.fields, null, 2)}</pre>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>