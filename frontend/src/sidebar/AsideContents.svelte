<script lang="ts">
  import { urlFor } from "../helpers.ts";
  import { _ } from "../i18n.ts";
  import { keyboardShortcut } from "../keyboard-shortcuts.ts";
  import { errors, extensions, ledgerData } from "../stores/index.ts";
  import AccountSelector from "./AccountSelector.svelte";
  import Link from "./SidebarLink.svelte";

  const truncate = (s: string) => (s.length < 25 ? s : `${s.slice(25)}…`);

  let user_queries = $derived($ledgerData.user_queries);
  let sidebar_links = $derived($ledgerData.sidebar_links);
  let extension_reports = $derived(
    $extensions.filter((e) => e.report_title != null),
  );
</script>

{#if sidebar_links.length}
  <ul class="navigation">
    {#each sidebar_links as [label, link] (link)}
      <Link report={link} name={label} remote />
    {/each}
  </ul>
{/if}
<div class="nav-group-label card-label">{_("Dashboards")}</div>
<ul class="navigation">
  <Link report="dashboard" name={_("Overview")} key="g D" />
  <Link report="net_worth" name={_("Net worth")} key="g n" />
  <Link report="holdings_live" name={_("Holdings")} key="g h" />
  <Link report="predictions" name={_("Predictions")} key="g p" />
</ul>
<div class="nav-group-label card-label">{_("Ledger")}</div>
<ul class="navigation">
  <Link report="income_statement" name={_("Income Statement")} key="g i" />
  <Link report="balance_sheet" name={_("Balance Sheet")} key="g b" />
  <Link report="trial_balance" name={_("Trial Balance")} key="g t" />
  <Link report="journal" name={_("Journal")} key="g j">
    <a
      href="#add-transaction"
      class="secondary add-transaction"
      title={_("Add Journal Entry")}
      {@attach keyboardShortcut("n")}>+</a
    >
  </Link>
  <Link report="query" name={_("Query")} key="g q">
    {#if user_queries.length}
      <ul class="submenu">
        {#each user_queries as { query_string, name } (query_string)}
          <li>
            <a href={$urlFor("query/", { query_string })}>{truncate(name)}</a>
          </li>
        {/each}
      </ul>
    {/if}
  </Link>
  <AccountSelector />
</ul>
<ul class="navigation">
  {#if $errors.length > 0}
    <Link
      report="errors"
      name={_("Errors")}
      bubble={[$errors.length, "error"]}
    />
  {/if}
  <Link report="options" name={_("Options")} key="g o">
    <a href="#export" class="secondary" title={_("Export")}>⬇</a>
  </Link>
  <Link report="help" name={_("Help")} key="g H" />
</ul>
{#if extension_reports.length}
  <ul class="navigation">
    {#each extension_reports as ext (ext.name)}
      <Link report={`extension/${ext.name}`} name={ext.report_title ?? ""} />
    {/each}
  </ul>
{/if}

<style>
  .navigation {
    padding-bottom: 0.5rem;
    margin: 0;
  }

  .navigation + .navigation {
    padding-top: 0.5rem;
    border-top: 1px solid var(--sidebar-border);
  }

  .nav-group-label {
    padding: 0.5em 0.5em 0.25em 1em;
  }

  a {
    display: block;
    padding: 0.25em 0.5em 0.25em 1em;
    color: inherit;
  }

  a:hover {
    color: var(--sidebar-hover-color);
    background-color: var(--sidebar-border);
  }

  .secondary {
    width: 30px;
    padding: 3px 9px;
    line-height: 22px;
    color: inherit;
    background-color: var(--sidebar-background);
  }

  .add-transaction {
    font-size: 23px;
  }

  .submenu {
    width: 100%;
    margin: 0 0 0.5em;
  }

  .submenu a {
    width: 100%;
    padding-left: 35px;
  }

  .submenu li {
    font-size: 0.9em;
  }
</style>
