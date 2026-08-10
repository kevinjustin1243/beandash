<script lang="ts">
  import type { ParsedFavaChart } from "../../charts/index.ts";
  import { _ } from "../../i18n.ts";
  import {
    build_net_worth_chart_geometry,
    extract_net_worth_series,
    NET_WORTH_CHART_HEIGHT,
    NET_WORTH_CHART_WIDTH,
  } from "./net_worth_chart.ts";

  let { charts, currency }: { charts: ParsedFavaChart[]; currency: string } =
    $props();

  let geometry = $derived(
    build_net_worth_chart_geometry(
      extract_net_worth_series(charts, currency),
    ),
  );
</script>

{#if geometry}
  <div class="net-worth-chart">
    <svg
      viewBox="0 0 {NET_WORTH_CHART_WIDTH} {NET_WORTH_CHART_HEIGHT}"
      preserveAspectRatio="none"
    >
      <line
        class="gridline"
        x1="0"
        y1={NET_WORTH_CHART_HEIGHT * 0.25}
        x2={NET_WORTH_CHART_WIDTH}
        y2={NET_WORTH_CHART_HEIGHT * 0.25}
      ></line>
      <line
        class="gridline"
        x1="0"
        y1={NET_WORTH_CHART_HEIGHT * 0.5}
        x2={NET_WORTH_CHART_WIDTH}
        y2={NET_WORTH_CHART_HEIGHT * 0.5}
      ></line>
      <line
        class="gridline"
        x1="0"
        y1={NET_WORTH_CHART_HEIGHT * 0.75}
        x2={NET_WORTH_CHART_WIDTH}
        y2={NET_WORTH_CHART_HEIGHT * 0.75}
      ></line>
      <path class="area" d={geometry.area_path}></path>
      <path class="line" d={geometry.line_path}></path>
      {#if geometry.band_path}
        <path class="band" d={geometry.band_path}></path>
      {/if}
      {#if geometry.forecast_path}
        <path class="forecast" d={geometry.forecast_path}></path>
      {/if}
      <line
        class="today-marker"
        x1={geometry.split_x}
        y1="0"
        x2={geometry.split_x}
        y2={NET_WORTH_CHART_HEIGHT}
      ></line>
    </svg>
    <div class="axis-labels">
      <span>{geometry.axis_start}</span>
      <span>{geometry.axis_mid}</span>
      <span>{_("today")}</span>
      <span>{geometry.axis_end}</span>
    </div>
  </div>
  <div class="legend">
    <div><span class="swatch actual"></span>{_("actual")}</div>
    {#if geometry.forecast_path}
      <div><span class="swatch forecast"></span>{_("forecast")}</div>
      <div><span class="swatch band"></span>{_("80% band")}</div>
    {/if}
  </div>
{/if}

<style>
  .net-worth-chart {
    position: relative;
    height: 232px;
  }

  svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .gridline {
    stroke: var(--border-lighter);
    stroke-width: 1;
    vector-effect: non-scaling-stroke;
  }

  .area {
    fill: color-mix(in srgb, var(--green) 10%, transparent);
  }

  .line {
    fill: none;
    stroke: var(--green);
    stroke-width: 2;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .band {
    fill: color-mix(in srgb, var(--accent-forecast) 13%, transparent);
  }

  .forecast {
    fill: none;
    stroke: var(--accent-forecast);
    stroke-width: 2;
    stroke-dasharray: 5 5;
    vector-effect: non-scaling-stroke;
  }

  .today-marker {
    stroke: var(--border-darker);
    stroke-width: 1;
    stroke-dasharray: 3 4;
    vector-effect: non-scaling-stroke;
  }

  .axis-labels {
    position: absolute;
    right: 0;
    bottom: -4px;
    left: 0;
    display: flex;
    justify-content: space-between;
    font-family: var(--font-family-monospaced);
    font-size: 10px;
    color: var(--text-color-lightest);
  }

  .legend {
    display: flex;
    gap: 18px;
    padding-bottom: 10px;
    font-family: var(--font-family-monospaced);
    font-size: 10px;
    color: var(--text-color-lightest);
  }

  .legend div {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .swatch {
    display: inline-block;
    width: 14px;
    height: 2px;
  }

  .swatch.actual {
    background: var(--green);
  }

  .swatch.forecast {
    background: var(--accent-forecast);
  }

  .swatch.band {
    height: 8px;
    background: color-mix(in srgb, var(--accent-forecast) 25%, transparent);
  }
</style>
