<script lang="ts">
  import type { Predictions } from "../../api/validators.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let { predictions }: { predictions: Predictions } = $props();
</script>

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

<style>
  .forecast-tiles {
    display: grid;
    grid-column: 1 / -1;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1em;
  }

  .forecast-tiles .stat-value {
    font-size: 1.75em;
  }
</style>
