<script lang="ts">
  import ChartSwitcher from "../../charts/ChartSwitcher.svelte";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";
  import type { DashboardReportProps } from "./index.ts";
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
  }: DashboardReportProps = $props();
</script>

<div class="dashboard-grid">
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
          {netWorthChange >= 0 ? "+" : ""}{$ctx.amount(
            netWorthChange,
            currency,
          )}
        </span>
      {/if}
    </div>
    <div class="hero-secondary">
      <div>
        <div class="card-label">{_("Projected (12M)")}</div>
        <div class="stat-value stat-forecast">
          {$ctx.amount(predictions.net_worth_projected, predictions.currency)}
        </div>
        <div class="stat-muted">r² {predictions.net_worth_r_squared.toFixed(2)}</div>
      </div>
      {#if predictions.savings_rate != null}
        <div>
          <div class="card-label">{_("Savings rate")}</div>
          <div class="stat-value">{$ctx.percentage(predictions.savings_rate)}</div>
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

  {#if uncategorized}
    <Suggester {uncategorized} />
  {/if}

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

  <div class="forecast-tiles">
    <div class="card">
      <div class="card-label">{_("Net worth (12M)")}</div>
      <div class="stat-value stat-forecast">
        {$ctx.amount(predictions.net_worth_projected, predictions.currency)}
      </div>
    </div>
    <div class="card">
      <div class="card-label">{_("Spend next month")}</div>
      <div class="stat-value">
        {predictions.spend_next_period != null
          ? $ctx.amount(predictions.spend_next_period, predictions.currency)
          : "—"}
      </div>
    </div>
    <div class="card">
      <div class="card-label">{_("Cash flow (90D)")}</div>
      <div
        class="stat-value"
        class:stat-positive={(predictions.cash_flow_90d ?? 0) >= 0}
        class:stat-negative={(predictions.cash_flow_90d ?? 0) < 0}
      >
        {predictions.cash_flow_90d != null
          ? $ctx.amount(predictions.cash_flow_90d, predictions.currency)
          : "—"}
      </div>
    </div>
    <div class="card">
      <div class="card-label">{_("FI target")}</div>
      <div class="stat-value">
        {$ctx.amount(predictions.fi_target, predictions.currency)}
      </div>
      {#if predictions.fi_years != null}
        <div class="stat-muted">
          {format(_("in %(years)s years"), {
            years: predictions.fi_years.toFixed(1),
          })}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1em;
  }

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

  .stat-value {
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

  .forecast-tiles {
    display: grid;
    grid-column: 1 / -1;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1em;
  }
</style>
