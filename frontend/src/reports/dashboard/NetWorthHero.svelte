<script lang="ts">
  import type { Predictions } from "../../api/validators.ts";
  import ChartSwitcher from "../../charts/ChartSwitcher.svelte";
  import type { ParsedFavaChart } from "../../charts/index.ts";
  import { _ } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let {
    charts,
    currency,
    unrealizedGain,
    netWorth,
    netWorthChange,
    predictions,
  }: {
    charts: ParsedFavaChart[];
    currency: string;
    unrealizedGain: number | null;
    netWorth: number | null;
    netWorthChange: number | null;
    predictions: Predictions;
  } = $props();
</script>

<div class="card hero">
  <div class="card-label">{_("Net Worth")}</div>
  <div class="hero-headline">
    <span class="stat-value">
      {netWorth != null ? $ctx.amount(netWorth, currency) : "—"}
    </span>
    {#if netWorthChange != null}
      <span
        class="stat-delta"
        class:stat-positive={netWorthChange >= 0}
        class:stat-negative={netWorthChange < 0}
      >
        {netWorthChange >= 0 ? "+" : ""}{$ctx.amount(netWorthChange, currency)}
      </span>
    {/if}
  </div>
  <div class="hero-secondary">
    <div>
      <div class="card-label">{_("Projected (12M)")}</div>
      <div class="stat-value stat-forecast">
        {$ctx.amount(predictions.net_worth_projected, predictions.currency)}
      </div>
      <div class="stat-muted">
        r² {predictions.net_worth_r_squared.toFixed(2)}
      </div>
    </div>
    {#if predictions.savings_rate != null}
      <div>
        <div class="card-label">{_("Savings rate")}</div>
        <div class="stat-value">
          {$ctx.percentage(predictions.savings_rate)}
        </div>
      </div>
    {/if}
    {#if unrealizedGain != null}
      <div>
        <div class="card-label">{_("Unrealized gain")}</div>
        <div
          class="stat-value"
          class:stat-positive={unrealizedGain >= 0}
          class:stat-negative={unrealizedGain < 0}
        >
          {$ctx.amount(unrealizedGain, currency)}
        </div>
      </div>
    {/if}
  </div>
  <ChartSwitcher {charts} />
</div>

<style>
  .hero {
    grid-column: 1 / -1;
  }

  .hero-headline {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75em;
    align-items: baseline;
    margin: 0.25em 0 1em;
  }

  .hero-headline .stat-value {
    font-size: 2em;
  }

  .hero-headline .stat-delta {
    font-family: var(--font-family-monospaced);
    font-size: 1.1em;
  }

  .hero-secondary {
    display: flex;
    flex-wrap: wrap;
    gap: 2em;
    margin-bottom: 1em;
  }

  .hero-secondary .stat-value {
    font-size: 1.1em;
  }
</style>
