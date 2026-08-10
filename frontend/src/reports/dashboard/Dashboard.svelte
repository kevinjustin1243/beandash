<script lang="ts">
  import { _ } from "../../i18n.ts";
  import ForecastTiles from "./ForecastTiles.svelte";
  import HoldingsPreview from "./HoldingsPreview.svelte";
  import type { DashboardReportProps } from "./index.ts";
  import NetWorthHero from "./NetWorthHero.svelte";
  import OverviewHeader from "./OverviewHeader.svelte";
  import Suggester from "./Suggester.svelte";

  let {
    charts,
    currency,
    unrealizedGain,
    netWorth,
    netWorthChange,
    insights,
    predictions,
    uncategorized,
    holdings,
    commodities,
  }: DashboardReportProps = $props();
</script>

<div class="dashboard-grid">
  <OverviewHeader />

  <NetWorthHero
    {charts}
    {currency}
    {unrealizedGain}
    {netWorth}
    {netWorthChange}
    {predictions}
  />

  {#if uncategorized}
    <Suggester {uncategorized} />
  {/if}

  <HoldingsPreview {holdings} {commodities} />

  {#if insights.length}
    <div class="card insights-card">
      <div class="card-label">{_("What changed")}</div>
      <ul class="insights">
        {#each insights as insight (insight.entry_hash)}
          <li class={`insight insight-${insight.type}`}>
            <a href={`#context-${insight.entry_hash}`}>{insight.message}</a>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <ForecastTiles {predictions} />
</div>

<style>
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1em;
  }

  .insights {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .insight {
    padding: 0.4em 0 0.4em 0.75em;
    border-left: 3px solid var(--border);
  }

  .insight-new_payee {
    border-left-color: var(--accent-forecast);
  }

  .insight-unusual_transaction {
    border-left-color: var(--warning);
  }
</style>
