<script lang="ts">
  import type { Predictions } from "../../api/validators.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let { predictions }: { predictions: Predictions } = $props();

  function clamp_pct(value: number): number {
    return Math.max(0, Math.min(100, value));
  }

  function signed_pct(value: number): string {
    const rounded = Math.round(value);
    return `${rounded >= 0 ? "+" : ""}${rounded.toString()}%`;
  }

  const net_worth_delta = $derived(
    predictions.net_worth > 0
      ? (predictions.net_worth_projected / predictions.net_worth - 1) * 100
      : null,
  );
  const net_worth_meter = $derived(
    clamp_pct(predictions.net_worth_r_squared * 100),
  );

  const spend_ratio = $derived(
    predictions.spend_next_period != null &&
      predictions.spend_trailing_monthly > 0
      ? (predictions.spend_next_period / predictions.spend_trailing_monthly -
          1) *
          100
      : null,
  );
  const spend_meter = $derived(
    predictions.spend_next_period != null &&
      predictions.spend_trailing_monthly > 0
      ? clamp_pct(
          (predictions.spend_next_period / predictions.spend_trailing_monthly) *
            100,
        )
      : 0,
  );

  const trailing_annual_spend = $derived(
    predictions.spend_trailing_monthly * 12,
  );
  const cash_flow_ratio = $derived(
    predictions.cash_flow_90d != null && trailing_annual_spend > 0
      ? (predictions.cash_flow_90d / (trailing_annual_spend / 4)) * 100
      : null,
  );
  const cash_flow_meter = $derived(
    cash_flow_ratio != null ? clamp_pct(cash_flow_ratio) : 0,
  );

  const fi_progress = $derived(
    predictions.fi_target > 0
      ? clamp_pct((predictions.net_worth / predictions.fi_target) * 100)
      : 0,
  );
</script>

<div class="forecast-tiles">
  <div class="card">
    <div class="card-label">{_("Net worth (12M)")}</div>
    <div class="stat-value stat-forecast">
      {$ctx.amount(predictions.net_worth_projected, predictions.currency)}
    </div>
    <div class="tile-meter">
      <span class="tile-meter-bar">
        <span
          class="tile-meter-fill tile-meter-forecast"
          style:width="{net_worth_meter}%"
        ></span>
      </span>
      {#if net_worth_delta != null}
        <span
          class="tile-delta"
          class:stat-positive={net_worth_delta >= 0}
          class:stat-negative={net_worth_delta < 0}
        >
          {signed_pct(net_worth_delta)}
        </span>
      {/if}
    </div>
    {#if predictions.net_worth_monthly_change != null}
      <div class="stat-muted tile-note">
        {format(_("at current %(change)s/mo trend"), {
          change: $ctx.amount(
            predictions.net_worth_monthly_change,
            predictions.currency,
          ),
        })}
      </div>
    {/if}
  </div>
  <div class="card">
    <div class="card-label">{_("Spend next month")}</div>
    <div class="stat-value">
      {predictions.spend_next_period != null
        ? $ctx.amount(predictions.spend_next_period, predictions.currency)
        : "—"}
    </div>
    {#if spend_ratio != null}
      <div class="tile-meter">
        <span class="tile-meter-bar">
          <span
            class="tile-meter-fill tile-meter-warning"
            style:width="{spend_meter}%"
          ></span>
        </span>
        <span class="tile-delta stat-warning">{signed_pct(spend_ratio)}</span>
      </div>
      <div class="stat-muted tile-note">
        {_("trend fit vs. recent average")}
      </div>
    {/if}
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
    {#if cash_flow_ratio != null}
      <div class="tile-meter">
        <span class="tile-meter-bar">
          <span
            class="tile-meter-fill"
            class:tile-meter-positive={cash_flow_ratio >= 0}
            class:tile-meter-negative={cash_flow_ratio < 0}
            style:width="{cash_flow_meter}%"
          ></span>
        </span>
        <span
          class="tile-delta"
          class:stat-positive={cash_flow_ratio >= 0}
          class:stat-negative={cash_flow_ratio < 0}
        >
          {signed_pct(cash_flow_ratio)}
        </span>
      </div>
      <div class="stat-muted tile-note">
        {_("income minus expenses, projected")}
      </div>
    {/if}
  </div>
  <div class="card">
    <div class="card-label">{_("FI target")}</div>
    <div class="stat-value">
      {$ctx.amount(predictions.fi_target, predictions.currency)}
    </div>
    {#if predictions.fi_target > 0}
      <div class="tile-meter">
        <span class="tile-meter-bar">
          <span
            class="tile-meter-fill tile-meter-positive"
            style:width="{fi_progress}%"
          ></span>
        </span>
        <span class="tile-delta stat-positive">
          {Math.round(fi_progress)}%
        </span>
      </div>
    {/if}
    {#if predictions.fi_years != null}
      <div class="stat-muted tile-note">
        {format(_("in %(years)s years"), {
          years: predictions.fi_years.toFixed(1),
        })}
      </div>
    {/if}
  </div>
</div>

<style>
  .forecast-tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    grid-column: 1 / -1;
    gap: 1em;
  }

  .forecast-tiles .stat-value {
    font-size: 1.75em;
  }

  .tile-meter {
    display: flex;
    gap: 0.5em;
    align-items: center;
    margin-top: 0.6em;
  }

  .tile-meter-bar {
    flex: 1 1 auto;
    height: 4px;
    overflow: hidden;
    background-color: var(--border);
    border-radius: 4px;
  }

  .tile-meter-fill {
    display: block;
    height: 100%;
    border-radius: 4px;
  }

  .tile-meter-forecast {
    background-color: var(--accent-forecast);
  }

  .tile-meter-warning {
    background-color: var(--warning);
  }

  .tile-meter-positive {
    background-color: var(--green);
  }

  .tile-meter-negative {
    background-color: var(--red);
  }

  .tile-delta {
    flex: none;
    font-family: var(--font-family-monospaced);
    font-size: 0.8em;
    white-space: nowrap;
  }

  .tile-note {
    margin-top: 0.4em;
    font-size: 0.75em;
  }
</style>
