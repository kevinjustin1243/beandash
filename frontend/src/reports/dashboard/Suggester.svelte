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

  let accepting: string | null = $state(null);

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
    <div class="card-label">{_("Needs categorizing")}</div>
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
              disabled={accepting != null}
              onclick={() => {
                void accept(account);
              }}
            >
              <span class="suggester-suggestion-account">{account}</span>
              <span class="suggester-bar">
                <span
                  class="suggester-bar-fill"
                  style:width="{top_score > 0
                    ? Math.round((score / top_score) * 100).toString()
                    : '0'}%"
                ></span>
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
    <a class="suggester-edit" href={`#context-${uncategorized.entry_hash}`}>
      {_("Edit manually")}
    </a>
  </div>
{/if}

<style>
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
    padding: 0;
    margin: 0 0 1em;
    list-style: none;
  }

  .suggester-suggestion {
    display: flex;
    gap: 0.75em;
    align-items: center;
    width: 100%;
    padding: 0.4em 0;
    font: inherit;
    color: inherit;
    text-align: left;
    background: none;
    border: none;
    cursor: pointer;
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
    height: 6px;
    overflow: hidden;
    background-color: var(--background-darkest);
    border-radius: 3px;
  }

  .suggester-bar-fill {
    display: block;
    height: 100%;
    background-color: var(--green);
    border-radius: 3px;
  }

  .suggester-edit {
    font-size: 0.85em;
  }
</style>
