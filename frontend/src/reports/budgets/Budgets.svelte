<script lang="ts">
  import type { BudgetAccountProgress } from "../../api/validators.ts";
  import { day } from "../../format.ts";
  import { urlFor } from "../../helpers.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";
  import type { BudgetsReportProps } from "./index.ts";

  let { report }: BudgetsReportProps = $props();

  function clamp_pct(value: number): number {
    return Math.max(0, Math.min(100, value));
  }

  type Tone = "positive" | "warning" | "negative";

  function tone(pct_used: number | null): Tone | null {
    if (pct_used == null) {
      return null;
    }
    if (pct_used >= 1) {
      return "negative";
    }
    if (pct_used >= 0.8) {
      return "warning";
    }
    return "positive";
  }

  function row_tone(row: BudgetAccountProgress): Tone | null {
    return tone(row.pct_used);
  }
</script>

{#if report.accounts.length}
  <div class="card budgets">
    <div class="budgets-header">
      <div class="card-label">{_("Budgets")}</div>
      <div class="stat-muted budgets-period">
        {day(report.date_range.begin)} – {day(report.date_range.end)}
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>{_("Account")}</th>
          <th></th>
          <th>{_("Budgeted")}</th>
          <th>{_("Actual")}</th>
          <th>{_("Remaining")}</th>
        </tr>
      </thead>
      <tbody>
        {#each report.accounts as row (row.account)}
          {@const t = row_tone(row)}
          <tr>
            <td>{row.account}</td>
            <td class="budgets-meter">
              {#if row.pct_used != null}
                {@const pct = clamp_pct(row.pct_used * 100)}
                <span class="tile-meter-bar">
                  <span
                    class="tile-meter-fill"
                    class:tile-meter-positive={t === "positive"}
                    class:tile-meter-warning={t === "warning"}
                    class:tile-meter-negative={t === "negative"}
                    style:width="{pct}%"
                  ></span>
                </span>
              {/if}
            </td>
            <td class="num">{$ctx.amount(row.budgeted, report.currency)}</td>
            <td class="num">{$ctx.amount(row.actual, report.currency)}</td>
            <td class="num">
              <span
                class:stat-positive={row.remaining >= 0}
                class:stat-negative={row.remaining < 0}
              >
                {$ctx.amount(row.remaining, report.currency)}
              </span>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    <div class="budgets-footer">
      <span class="stat-muted">
        {format(_("%(count)s budgeted categories"), {
          count: report.accounts.length.toString(),
        })}
      </span>
      <span>
        {format(_("%(actual)s of %(budgeted)s"), {
          actual: $ctx.amount(report.total_actual, report.currency),
          budgeted: $ctx.amount(report.total_budgeted, report.currency),
        })}
      </span>
    </div>
  </div>
{:else}
  <div class="card budgets-empty">
    <div class="card-label">{_("Budgets")}</div>
    <p>{_("No budgets configured for this period.")}</p>
    <p>
      {_("Declare one with a custom directive anywhere in your ledger:")}
    </p>
    <pre><code
        >2026-01-01 custom "budget" Expenses:Groceries "monthly" 400.00 USD</code
      ></pre>
    <a href={$urlFor("help/budgets")}>{_("Learn more")}</a>
  </div>
{/if}

<style>
  .budgets-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 0.75em;
  }

  .budgets-period {
    font-family: var(--font-family-monospaced);
    font-size: 0.8em;
  }

  table {
    width: 100%;
    font-family: var(--font-family-monospaced);
    font-size: 0.9em;
    border-collapse: collapse;
  }

  th {
    padding: 0.3em 0.5em;
    font-family: var(--font-family);
    font-size: 0.75em;
    font-weight: 600;
    color: var(--text-color-lightest);
    text-align: right;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  td {
    padding: 0.4em 0.5em;
    vertical-align: middle;
    text-align: right;
    border-top: 1px solid var(--border);
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  .budgets-meter {
    width: 30%;
    min-width: 80px;
  }

  .budgets-footer {
    display: flex;
    justify-content: space-between;
    padding-top: 0.6em;
    margin-top: 0.3em;
    font-family: var(--font-family-monospaced);
    font-size: 0.85em;
    border-top: 1px solid var(--border);
  }

  .budgets-empty pre {
    padding: 0.6em 0.8em;
    margin: 0.5em 0;
    overflow-x: auto;
    background-color: var(--background-darkest);
    border-radius: 8px;
  }
</style>
