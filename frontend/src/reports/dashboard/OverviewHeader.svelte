<script lang="ts">
  import { urlFor } from "../../helpers.ts";
  import { _, format } from "../../i18n.ts";
  import { router } from "../../router.ts";
  import { time_filter } from "../../stores/filters.ts";
  import { errors } from "../../stores/index.ts";

  const now = new Date();

  function greeting(): string {
    const hour = now.getHours();
    if (hour < 12) {
      return _("Good morning.");
    }
    if (hour < 18) {
      return _("Good afternoon.");
    }
    return _("Good evening.");
  }

  function iso(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  function monthsAgo(n: number): Date {
    return new Date(now.getFullYear(), now.getMonth() - n, now.getDate());
  }

  function yearsAgo(n: number): Date {
    return new Date(now.getFullYear() - n, now.getMonth(), now.getDate());
  }

  const today_iso = iso(now);
  const today_label = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(now);

  const presets: { label: string; time: string }[] = [
    { label: "1M", time: `${iso(monthsAgo(1))} - ${today_iso}` },
    { label: "6M", time: `${iso(monthsAgo(6))} - ${today_iso}` },
    {
      label: "YTD",
      time: `${now.getFullYear().toString()}-01-01 - ${today_iso}`,
    },
    { label: "2Y", time: `${iso(yearsAgo(2))} - ${today_iso}` },
    { label: "ALL", time: "" },
  ];
</script>

<div class="overview-header">
  <div class="overview-header-text">
    <div class="card-label">
      {format(_("Overview · %(date)s"), { date: today_label })}
    </div>
    <h1>
      {greeting()}
      {#if $errors.length === 0}
        {_("Everything reconciled.")}
      {:else}
        <a href={$urlFor("errors/")}>
          {format(_("%(count)s error(s) to review."), {
            count: $errors.length.toString(),
          })}
        </a>
      {/if}
    </h1>
  </div>
  <div class="time-pills">
    {#each presets as preset (preset.label)}
      <button
        type="button"
        class:active={$time_filter === preset.time}
        onclick={() => {
          router.set_search_param("time", preset.time);
        }}
      >
        {preset.label}
      </button>
    {/each}
  </div>
</div>

<style>
  .overview-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1em;
    grid-column: 1 / -1;
  }

  h1 {
    margin: 0.25em 0 0;
    font-size: 1.6em;
    font-weight: 600;
    letter-spacing: -0.02em;
  }

  h1 a {
    color: var(--warning);
  }

  .time-pills {
    display: flex;
    padding: 3px;
    background-color: var(--background-darker);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .time-pills button {
    padding: 6px 11px;
    font-family: var(--font-family-monospaced);
    font-size: 0.75em;
    color: var(--text-color-lightest);
    background: none;
    border: none;
    border-radius: 7px;
    cursor: pointer;
  }

  .time-pills button.active {
    color: var(--text-color);
    background-color: var(--background-button);
  }
</style>
