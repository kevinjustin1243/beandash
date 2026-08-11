<script lang="ts">
  import type { Insight } from "../../api/validators.ts";
  import { _ } from "../../i18n.ts";

  let { insights }: { insights: Insight[] } = $props();
</script>

{#if insights.length}
  <div class="card insights-card">
    <div class="card-label">{_("What changed")}</div>
    <ul class="insights">
      {#each insights as insight (insight.entry_hash)}
        <li class="insight insight-tone-{insight.tone}">
          <a href={`#context-${insight.entry_hash}`}>
            <span class="insight-text">
              <span class="insight-title">{insight.title}</span>
              <span class="insight-detail stat-muted">{insight.detail}</span>
            </span>
            <span class="insight-value">{insight.value}</span>
          </a>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .insights {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .insight {
    border-left: 3px solid var(--border);
  }

  .insight-tone-amber {
    border-left-color: var(--warning);
  }

  .insight-tone-red {
    border-left-color: var(--error);
  }

  .insight a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75em;
    padding: 0.4em 0.5em 0.4em 0.75em;
    color: inherit;
  }

  .insight a:hover {
    background-color: var(--background-darkest);
  }

  .insight-text {
    display: flex;
    flex-direction: column;
    gap: 0.15em;
    min-width: 0;
  }

  .insight-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .insight-detail {
    font-size: 0.8em;
  }

  .insight-value {
    flex: none;
    font-family: var(--font-family-monospaced);
    font-size: 0.85em;
    color: var(--text-color-lightest);
  }

  .insight-tone-amber .insight-value {
    color: var(--warning);
  }

  .insight-tone-red .insight-value {
    color: var(--error);
  }
</style>
