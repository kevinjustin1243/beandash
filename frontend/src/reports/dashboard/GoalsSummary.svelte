<script lang="ts">
  import type { GoalProgress } from "../../api/validators.ts";
  import { urlFor } from "../../helpers.ts";
  import { _ } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let { goals }: { goals: GoalProgress[] } = $props();

  function clamp_pct(value: number): number {
    return Math.max(0, Math.min(100, value));
  }
</script>

{#if goals.length}
  <div class="card goals-summary">
    <div class="goals-summary-header">
      <div class="card-label">{_("Goals")}</div>
      <a href={$urlFor("goals/")}>{_("View all")}</a>
    </div>
    <ul class="goals-summary-list">
      {#each goals.slice(0, 3) as goal (goal.account + goal.label)}
        <li>
          <div class="goals-summary-row">
            <span>{goal.label}</span>
            <span class="stat-muted">
              {goal.pct_complete != null
                ? $ctx.percentage(goal.pct_complete)
                : "—"}
            </span>
          </div>
          {#if goal.pct_complete != null}
            {@const pct = clamp_pct(goal.pct_complete * 100)}
            <span class="tile-meter-bar">
              <span
                class="tile-meter-fill tile-meter-positive"
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
  .goals-summary-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 0.5em;
  }

  .goals-summary-header a {
    font-size: 0.8em;
  }

  .goals-summary-list {
    display: flex;
    flex-direction: column;
    gap: 0.6em;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .goals-summary-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.3em;
    font-size: 0.9em;
  }
</style>
