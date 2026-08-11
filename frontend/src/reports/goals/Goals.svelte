<script lang="ts">
  import { day } from "../../format.ts";
  import { urlFor } from "../../helpers.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";
  import type { GoalsReportProps } from "./index.ts";

  let { goals }: GoalsReportProps = $props();

  function clamp_pct(value: number): number {
    return Math.max(0, Math.min(100, value));
  }
</script>

{#if goals.length}
  <div class="goals-grid">
    {#each goals as goal (goal.account + goal.label)}
      <div class="card goal-card">
        <div class="goal-header">
          <div>
            <div class="card-label">{goal.label}</div>
            <div class="stat-muted goal-account">{goal.account}</div>
          </div>
          {#if goal.on_track != null}
            <span
              class="goal-badge"
              class:stat-positive={goal.on_track}
              class:stat-negative={!goal.on_track}
            >
              {goal.on_track ? _("On track") : _("Behind")}
            </span>
          {/if}
        </div>
        <div class="goal-amounts">
          <span class="stat-value">
            {$ctx.amount(goal.balance, goal.currency)}
          </span>
          <span class="stat-muted">
            {format(_("of %(target)s"), {
              target: $ctx.amount(goal.target, goal.currency),
            })}
          </span>
        </div>
        {#if goal.pct_complete != null}
          {@const pct = clamp_pct(goal.pct_complete * 100)}
          <div class="tile-meter">
            <span class="tile-meter-bar">
              <span
                class="tile-meter-fill tile-meter-positive"
                style:width="{pct}%"
              ></span>
            </span>
            <span class="tile-delta">{Math.round(pct)}%</span>
          </div>
        {/if}
        <div class="stat-muted goal-note">
          {#if goal.target_date != null}
            {format(_("target %(date)s"), { date: day(goal.target_date) })}
          {:else}
            {_("no target date")}
          {/if}
        </div>
      </div>
    {/each}
  </div>
{:else}
  <div class="card goals-empty">
    <div class="card-label">{_("Goals")}</div>
    <p>{_("No goals yet.")}</p>
    <p>
      {_("Declare one with a custom directive anywhere in your ledger:")}
    </p>
    <pre><code
        >2026-01-01 custom "goal" Assets:Savings "House fund" 50000.00 USD 2027-06-01</code
      ></pre>
    <a href={$urlFor("help/goals")}>{_("Learn more")}</a>
  </div>
{/if}

<style>
  .goals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1em;
  }

  .goal-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  .goal-account {
    margin-top: 0.2em;
    font-family: var(--font-family-monospaced);
    font-size: 0.8em;
  }

  .goal-badge {
    flex: none;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .goal-amounts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5em;
    align-items: baseline;
    margin: 0.5em 0;
  }

  .goal-note {
    margin-top: 0.4em;
    font-size: 0.8em;
  }

  .goals-empty pre {
    padding: 0.6em 0.8em;
    margin: 0.5em 0;
    overflow-x: auto;
    background-color: var(--background-darkest);
    border-radius: 8px;
  }
</style>
