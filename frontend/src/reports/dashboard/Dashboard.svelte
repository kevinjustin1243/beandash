<script lang="ts">
  import AllocationGrid from "./AllocationGrid.svelte";
  import ForecastTiles from "./ForecastTiles.svelte";
  import HoldingsPreview from "./HoldingsPreview.svelte";
  import InsightsPanel from "./InsightsPanel.svelte";
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
    holdingsReport,
    commodities,
    allocation,
    liquidCash,
  }: DashboardReportProps = $props();
</script>

<div class="dashboard-grid">
  <OverviewHeader />

  <div class="hero-row">
    <NetWorthHero
      {charts}
      {currency}
      {unrealizedGain}
      {netWorth}
      {netWorthChange}
      {predictions}
    />
    <AllocationGrid
      {allocation}
      {liquidCash}
      {predictions}
      {unrealizedGain}
      {currency}
    />
  </div>

  {#if uncategorized}
    <Suggester {uncategorized} />
  {/if}

  <HoldingsPreview {holdingsReport} {commodities} />

  <InsightsPanel {insights} />

  <ForecastTiles {predictions} />
</div>

<style>
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1em;
  }

  .hero-row {
    display: grid;
    grid-column: 1 / -1;
    grid-template-columns: minmax(0, 1.9fr) minmax(260px, 1fr);
    gap: 1em;
  }

  @media (width <= 900px) {
    .hero-row {
      grid-template-columns: 1fr;
    }
  }
</style>
