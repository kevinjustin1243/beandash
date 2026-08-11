<script lang="ts">
  import type { BudgetReport } from "../../api/validators.ts";
  import { urlFor } from "../../helpers.ts";
  import { _ } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let { report }: { report: BudgetReport } = $props();

  function clamp_pct(value: number): number {
    return Math.max(0, Math.min(100, value));
  }
</script>

{#if report.accounts.length}
  <div class="card budgets-summary">
    <div class="budgets-summary-header">
      <div class="card-label">{_("Budgets")}</div>
      <a href={$urlFor("budgets/")}>{_("View all")}</a>
    </div>
    <ul class="budgets-summary-list">
      {#each report.accounts.slice(0, 3) as row (row.account)}
        <li>
          <div class="budgets-summary-row">
            <span>{row.account}</span>
            <span
              class:stat-negative={row.pct_used != null && row.pct_used >= 1}
              class:stat-warning={row.pct_used != null &&
                row.pct_used >= 0.8 &&
                row.pct_used < 1}
            >
              {row.pct_used != null ? $ctx.percentage(row.pct_used) : "—"}
            </span>
          </div>
          {#if row.pct_used != null}
            {@const pct = clamp_pct(row.pct_used * 100)}
            <span class="tile-meter-bar">
              <span
                class="tile-meter-fill"
                class:tile-meter-negative={row.pct_used >= 1}
                class:tile-meter-warning={row.pct_used >= 0.8 &&
                  row.pct_used < 1}
                class:tile-meter-positive={row.pct_used < 0.8}
                style:width="{pct}%"
              ></span>
            </span>
          {/if}
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .budgets-summary-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 0.5em;
  }

  .budgets-summary-header a {
    font-size: 0.8em;
  }

  .budgets-summary-list {
    display: flex;
    flex-direction: column;
    gap: 0.6em;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .budgets-summary-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.3em;
    font-size: 0.9em;
  }
</style>
