<script lang="ts">
  import AllocationGrid from "./AllocationGrid.svelte";
  import ForecastTiles from "./ForecastTiles.svelte";
  import GoalsSummary from "./GoalsSummary.svelte";
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
    goals,
  }: DashboardReportProps = $props();
</script>

<div class="dashboard-grid">
  <OverviewHeader />

  <div class="hero-row">
    <NetWorthHero
      {charts}
      {currency}
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

  <GoalsSummary {goals} />

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
    grid-template-columns: minmax(0, 1.9fr) minmax(260px, 1fr);
    grid-column: 1 / -1;
    gap: 1em;
  }

  @media (width <= 900px) {
    .hero-row {
      grid-template-columns: 1fr;
    }
  }
</style>
