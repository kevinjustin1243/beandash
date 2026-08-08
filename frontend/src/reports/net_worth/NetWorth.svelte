<script lang="ts">
  import NetWorthHero from "../dashboard/NetWorthHero.svelte";
  import type { NetWorthReportProps } from "./index.ts";

  let {
    charts,
    currency,
    unrealizedGain,
    netWorth,
    netWorthChange,
    predictions,
  }: NetWorthReportProps = $props();
</script>

<div class="net-worth-page">
  <NetWorthHero
    {charts}
    {currency}
    {unrealizedGain}
    {netWorth}
    {netWorthChange}
    {predictions}
  />
</div>

<style>
  .net-worth-page {
    display: grid;
    gap: 1em;
  }
</style>
