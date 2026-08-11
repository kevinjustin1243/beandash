<script lang="ts">
  import { get_source_slice, put_source_slice } from "../../api/index.ts";
  import type { UncategorizedTransaction } from "../../api/validators.ts";
  import { Transaction } from "../../entries/index.ts";
  import { _ } from "../../i18n.ts";
  import { notify, notify_err } from "../../notifications.ts";
  import { router } from "../../router.ts";

  let {
    uncategorized,
  }: {
    uncategorized: NonNullable<UncategorizedTransaction>;
  } = $props();

  const entry = $derived(uncategorized.entry);
  const top_score = $derived(uncategorized.suggestions[0]?.[1] ?? 0);
  const top_account = $derived(uncategorized.suggestions[0]?.[0]);

  let accepting: string | null = $state(null);

  function match_pct(score: number): number {
    return top_score > 0 ? Math.round((score / top_score) * 100) : 0;
  }

  async function accept(account: string): Promise<void> {
    accepting = account;
    try {
      const { slice, sha256sum } = await get_source_slice({
        entry_hash: uncategorized.entry_hash,
      });
      const source = slice.replace(uncategorized.placeholder_account, account);
      const msg = await put_source_slice({
        entry_hash: uncategorized.entry_hash,
        source,
        sha256sum,
      });
      notify(msg);
      router.reload();
    } catch (error) {
      notify_err(error);
    } finally {
      accepting = null;
    }
  }
</script>

{#if entry instanceof Transaction}
  <div class="card suggester">
    <div class="suggester-header">
      <div class="card-label">{_("Needs categorizing")}</div>
      <div class="stat-muted suggester-subtitle">
        {_("awaiting categorization")}
      </div>
    </div>
    <div class="suggester-entry">
      <span class="suggester-date">{entry.date}</span>
      <span class="suggester-payee">{entry.payee || entry.narration}</span>
      {#if entry.payee && entry.narration}
        <span class="stat-muted">{entry.narration}</span>
      {/if}
    </div>
    <ul class="suggester-postings">
      {#each entry.postings as posting (posting.account + posting.amount)}
        <li class:suggester-placeholder={posting.account ===
          uncategorized.placeholder_account}
        >
          <span>{posting.account}</span>
          <span class="suggester-amount">{posting.amount}</span>
        </li>
      {/each}
    </ul>
    {#if uncategorized.suggestions.length}
      <ul class="suggester-suggestions">
        {#each uncategorized.suggestions as [account, score] (account)}
          <li>
            <button
              type="button"
              class="suggester-suggestion"
              class:suggester-suggestion-top={account === top_account}
              disabled={accepting != null}
              onclick={() => {
                void accept(account);
              }}
            >
              <span class="suggester-suggestion-account">{account}</span>
              <span class="suggester-bar">
                <span
                  class="suggester-bar-fill"
                  style:width="{match_pct(score).toString()}%"
                ></span>
              </span>
              <span class="suggester-suggestion-pct">{match_pct(score)}%</span
              >
            </button>
          </li>
        {/each}
      </ul>
    {/if}
    <div class="suggester-actions">
      {#if top_account}
        <button
          type="button"
          class="suggester-accept-top"
          disabled={accepting != null}
          onclick={() => {
            void accept(top_account);
          }}
        >
          {_("Accept top match")}
        </button>
      {/if}
      <a class="suggester-edit" href={`#context-${uncategorized.entry_hash}`}>
        {_("Edit manually")}
      </a>
    </div>
  </div>
{/if}

<style>
  .suggester-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  .suggester-subtitle {
    margin-top: 0.2em;
    font-size: 0.8em;
  }

  .suggester-entry {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5em;
    align-items: baseline;
    margin: 0.5em 0;
  }

  .suggester-date {
    font-family: var(--font-family-monospaced);
    color: var(--text-color-lightest);
  }

  .suggester-payee {
    font-weight: 600;
  }

  .suggester-postings {
    padding: 0;
    margin: 0 0 1em;
    list-style: none;
  }

  .suggester-postings li {
    display: flex;
    justify-content: space-between;
    padding: 0.25em 0;
    font-family: var(--font-family-monospaced);
    font-size: 0.9em;
  }

  .suggester-placeholder {
    color: var(--warning);
  }

  .suggester-suggestions {
    display: flex;
    flex-direction: column;
    gap: 0.5em;
    padding: 0;
    margin: 0 0 1em;
    list-style: none;
  }

  .suggester-suggestion {
    display: flex;
    gap: 0.6em;
    align-items: center;
    width: 100%;
    padding: 0.5em 0.7em;
    font: inherit;
    color: inherit;
    text-align: left;
    background-color: var(--background-darkest);
    border: 1px solid var(--border);
    border-radius: 9px;
    cursor: pointer;
  }

  .suggester-suggestion-top {
    background-color: color-mix(in srgb, var(--green) 12%, var(--background-darkest));
    border-color: color-mix(in srgb, var(--green) 45%, var(--border));
  }

  .suggester-suggestion:disabled {
    cursor: default;
    opacity: 0.5;
  }

  .suggester-suggestion-account {
    flex: 0 0 auto;
    font-family: var(--font-family-monospaced);
    font-size: 0.9em;
  }

  .suggester-bar {
    flex: 1 1 auto;
    height: 3px;
    margin-left: auto;
    overflow: hidden;
    background-color: var(--border);
    border-radius: 3px;
  }

  .suggester-bar-fill {
    display: block;
    height: 100%;
    background-color: var(--green);
    border-radius: 3px;
  }

  .suggester-suggestion-pct {
    flex: 0 0 auto;
    width: 2.5em;
    font-family: var(--font-family-monospaced);
    font-size: 0.8em;
    color: var(--text-color-lightest);
    text-align: right;
  }

  .suggester-actions {
    display: flex;
    gap: 0.5em;
  }

  .suggester-accept-top {
    flex: 1 1 auto;
    padding: 0.55em;
    font-weight: 600;
    font-size: 0.85em;
    color: var(--background-darker);
    text-align: center;
    cursor: pointer;
    background-color: var(--green);
    border: none;
    border-radius: 9px;
  }

  .suggester-accept-top:disabled {
    cursor: default;
    opacity: 0.5;
  }

  .suggester-edit {
    display: flex;
    align-items: center;
    padding: 0.55em 0.9em;
    font-size: 0.85em;
    color: var(--text-color-lightest);
    border: 1px solid var(--border);
    border-radius: 9px;
  }
</style>
