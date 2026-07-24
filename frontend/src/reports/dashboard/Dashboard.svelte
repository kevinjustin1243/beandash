<script lang="ts">
  import ChartSwitcher from "../../charts/ChartSwitcher.svelte";
  import { _ } from "../../i18n.ts";
  import type { DashboardReportProps } from "./index.ts";

  let { charts, insights }: DashboardReportProps = $props();
</script>

<ChartSwitcher {charts} />

{#if insights.length}
  <h3>{_("Insights")}</h3>
  <ul class="insights">
    {#each insights as insight (insight.entry_hash)}
      <li>
        <a href={`#context-${insight.entry_hash}`}>{insight.message}</a>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .insights {
    padding-left: 1.5em;
    margin: 0;
  }
</style>
