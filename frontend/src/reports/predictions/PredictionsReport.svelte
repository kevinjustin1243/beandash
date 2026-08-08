<script lang="ts">
  import ChartSwitcher from "../../charts/ChartSwitcher.svelte";
  import { _ } from "../../i18n.ts";
  import ForecastTiles from "../dashboard/ForecastTiles.svelte";
  import type { PredictionsReportProps } from "./index.ts";

  let { predictions, net_worth_chart }: PredictionsReportProps = $props();
</script>

<div class="predictions-page">
  <ForecastTiles {predictions} />
  {#if net_worth_chart}
    <div class="card forecast-chart">
      <div class="card-label">{_("Net worth forecast")}</div>
      <ChartSwitcher charts={[net_worth_chart]} />
    </div>
  {/if}
</div>

<style>
  .predictions-page {
    display: grid;
    gap: 1em;
  }
</style>
