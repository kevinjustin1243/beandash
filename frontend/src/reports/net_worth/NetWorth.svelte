<script lang="ts">
  import AllocationGrid from "../dashboard/AllocationGrid.svelte";
  import NetWorthHero from "../dashboard/NetWorthHero.svelte";
  import type { NetWorthReportProps } from "./index.ts";

  let {
    charts,
    currency,
    unrealizedGain,
    netWorth,
    netWorthChange,
    predictions,
    allocation,
    liquidCash,
  }: NetWorthReportProps = $props();
</script>

<div class="net-worth-page">
  <NetWorthHero {charts} {currency} {netWorth} {netWorthChange} {predictions} />
  <AllocationGrid
    {allocation}
    {liquidCash}
    {predictions}
    {unrealizedGain}
    {currency}
  />
</div>

<style>
  .net-worth-page {
    display: grid;
    grid-template-columns: minmax(0, 1.9fr) minmax(260px, 1fr);
    gap: 1em;
  }

  @media (width <= 900px) {
    .net-worth-page {
      grid-template-columns: 1fr;
    }
  }
</style>
