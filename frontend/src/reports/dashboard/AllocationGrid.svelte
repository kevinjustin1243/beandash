<script lang="ts">
  import type { AllocationEntry, Predictions } from "../../api/validators.ts";
  import { colors10 } from "../../charts/helpers.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let {
    allocation,
    liquidCash,
    predictions,
    unrealizedGain,
    currency,
  }: {
    allocation: AllocationEntry[];
    liquidCash: number;
    predictions: Predictions;
    unrealizedGain: number | null;
    currency: string;
  } = $props();

  const LARGE_SHARE = 0.3;

  const cash_runway_months = $derived(
    predictions.spend_trailing_monthly > 0
      ? liquidCash / predictions.spend_trailing_monthly
      : null,
  );
</script>

<div class="card allocation">
  <div class="allocation-header">
    <div class="card-label">{_("Allocation")}</div>
    <div class="stat-muted">{_("Assets")}</div>
  </div>
  {#if allocation.length}
    <div class="tile-grid">
      {#each allocation as entry, i (entry.account)}
        <div
          class="tile"
          style:grid-row="span {entry.pct >= LARGE_SHARE ? 2 : 1}"
          style:background={colors10[i % colors10.length]}
        >
          <div class="tile-name">{entry.name}</div>
          <div class="tile-pct">{(entry.pct * 100).toFixed(0)}%</div>
        </div>
      {/each}
    </div>
  {/if}
  <div class="allocation-stats">
    <div class="allocation-stat">
      <span>{_("Equities drift vs. target")}</span>
      <span class="stat-muted">{_("not configured")}</span>
    </div>
    <div class="allocation-stat">
      <span>{_("Cash runway")}</span>
      <span>
        {cash_runway_months != null
          ? format(_("%(months)s months"), {
              months: cash_runway_months.toFixed(1),
            })
          : "—"}
      </span>
    </div>
    <div class="allocation-stat">
      <span>{_("Unrealized gains")}</span>
      <span
        class:stat-positive={unrealizedGain != null && unrealizedGain >= 0}
        class:stat-negative={unrealizedGain != null && unrealizedGain < 0}
      >
        {unrealizedGain != null ? $ctx.amount(unrealizedGain, currency) : "—"}
      </span>
    </div>
  </div>
</div>

<style>
  .allocation-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75em;
  }

  .tile-grid {
    display: grid;
    grid-auto-rows: 58px;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 1em;
  }

  .tile {
    display: flex;
    grid-column: span 2;
    flex-direction: column;
    justify-content: space-between;
    padding: 9px 10px;
    overflow: hidden;
    border-radius: 9px;
  }

  .tile-name {
    overflow: hidden;
    font-size: 11px;
    font-weight: 500;
    color: #06120d;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tile-pct {
    font-family: var(--font-family-monospaced);
    font-size: 11px;
    color: #06120d;
    opacity: 0.72;
  }

  .allocation-stats {
    display: flex;
    flex-direction: column;
    gap: 9px;
    padding-top: 0.75em;
    border-top: 1px solid var(--border);
  }

  .allocation-stat {
    display: flex;
    justify-content: space-between;
    font-size: 0.85em;
    color: var(--text-color-lightest);
  }

  .allocation-stat > span:last-child {
    font-family: var(--font-family-monospaced);
    color: var(--text-color);
  }
</style>
