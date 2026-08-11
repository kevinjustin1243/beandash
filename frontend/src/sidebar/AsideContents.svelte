<script lang="ts">
  import { urlFor } from "../helpers.ts";
  import { _, format } from "../i18n.ts";
  import { keyboardShortcut } from "../keyboard-shortcuts.ts";
  import { errors, extensions, ledgerData } from "../stores/index.ts";
  import AccountSelector from "./AccountSelector.svelte";
  import Link from "./SidebarLink.svelte";

  const truncate = (s: string) => (s.length < 25 ? s : `${s.slice(25)}…`);

  function basename(path: string): string {
    return path.split(/[/\\]/).pop() ?? path;
  }

  let user_queries = $derived($ledgerData.user_queries);
  let sidebar_links = $derived($ledgerData.sidebar_links);
  let extension_reports = $derived(
    $extensions.filter((e) => e.report_title != null),
  );
  let filename = $derived(basename($ledgerData.options.filename));
  let entries_count = $derived($ledgerData.entries_count);
</script>

<div class="brand">
  <div class="brand-mark">b</div>
  <div class="brand-name">Beandash</div>
</div>

{#if sidebar_links.length}
  <ul class="navigation">
    {#each sidebar_links as [label, link] (link)}
      <Link report={link} name={label} remote />
    {/each}
  </ul>
{/if}
<div class="nav-group-label card-label">{_("Dashboards")}</div>
<ul class="navigation">
  <Link report="dashboard" name={_("Overview")} key="g D" dot />
  <Link report="net_worth" name={_("Net worth")} key="g n" dot />
  <Link report="holdings_live" name={_("Holdings")} key="g h" dot />
  <Link report="predictions" name={_("Predictions")} key="g p" dot />
  <Link report="goals" name={_("Goals")} key="g g" dot />
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

<div class="sidebar-footer">
  <div class="sidebar-footer-filename">{filename}</div>
  <div class="sidebar-footer-status">
    <span class="pulse-dot"></span>
    <span>{_("Watching for changes")}</span>
  </div>
  <div class="sidebar-footer-counts">
    {format(_("%(entries)s entries · %(errors)s errors"), {
      entries: entries_count.toString(),
      errors: $errors.length.toString(),
    })}
  </div>
</div>

<style>
  .brand {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 0 0.5em 0.75em 1em;
  }

  .brand-mark {
    display: grid;
    flex: none;
    place-items: center;
    width: 26px;
    height: 26px;
    font-family: var(--font-family-monospaced);
    font-size: 14px;
    font-weight: 600;
    color: #06120d;
    background: linear-gradient(150deg, var(--green), #2c9c78);
    border-radius: 8px;
  }

  .brand-name {
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .sidebar-footer {
    padding: 0.75em 0.5em 0.5em 1em;
    margin-top: 0.5rem;
    font-size: 0.8em;
    border-top: 1px solid var(--sidebar-border);
  }

  .sidebar-footer-filename {
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: var(--font-family-monospaced);
    color: var(--sidebar-color);
    white-space: nowrap;
  }

  .sidebar-footer-status {
    display: flex;
    gap: 7px;
    align-items: center;
    padding-top: 4px;
    font-family: var(--font-family-monospaced);
    color: var(--green);
  }

  .pulse-dot {
    width: 6px;
    height: 6px;
    background-color: var(--green);
    border-radius: 50%;
    animation: sidebar-pulse 2s infinite;
  }

  .sidebar-footer-counts {
    padding-top: 4px;
    font-family: var(--font-family-monospaced);
    color: var(--text-color-lightest);
  }

  @keyframes sidebar-pulse {
    0%,
    100% {
      opacity: 1;
    }

    50% {
      opacity: 0.25;
    }
  }

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
