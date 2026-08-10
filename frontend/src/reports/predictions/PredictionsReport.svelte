<script lang="ts">
  import { _ } from "../../i18n.ts";
  import ForecastTiles from "../dashboard/ForecastTiles.svelte";
  import NetWorthChart from "../dashboard/NetWorthChart.svelte";
  import type { PredictionsReportProps } from "./index.ts";

  let { predictions, charts, currency }: PredictionsReportProps = $props();
</script>

<div class="predictions-page">
  <ForecastTiles {predictions} />
  <div class="card forecast-chart">
    <div class="card-label">{_("Net worth forecast")}</div>
    <NetWorthChart {charts} {currency} />
  </div>
</div>

<style>
  .predictions-page {
    display: grid;
    gap: 1em;
  }
</style>
