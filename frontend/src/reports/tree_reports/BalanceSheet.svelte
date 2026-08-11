<script lang="ts">
  import ChartSwitcher from "../../charts/ChartSwitcher.svelte";
  import TreeTable from "../../tree-table/TreeTable.svelte";
  import type { TreeReportProps } from "./index.ts";

  let { charts, trees, date_range }: TreeReportProps = $props();
  let end = $derived(date_range?.end ?? null);
</script>

<ChartSwitcher {charts} />

<div class="row">
  <div class="column">
    {#each trees.slice(0, 1) as tree (tree.account)}
      <div class="card tree-card">
        <TreeTable {tree} {end} />
      </div>
    {/each}
  </div>
  <div class="column">
    {#each trees.slice(1) as tree (tree.account)}
      <div class="card tree-card">
        <TreeTable {tree} {end} />
      </div>
    {/each}
  </div>
</div>

<style>
  .tree-card {
    overflow-x: auto;
  }

  .tree-card + .tree-card {
    margin-top: 1em;
  }
</style>
