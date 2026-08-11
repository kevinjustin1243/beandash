<script lang="ts">
  import { onMount } from "svelte";

  import { get_live_prices } from "../../api/index.ts";
  import type {
    Commodities,
    HoldingsReport,
    Quote,
  } from "../../api/validators.ts";
  import { _, format } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";
  import { ledgerData } from "../../stores/index.ts";

  let {
    holdingsReport,
    commodities,
  }: { holdingsReport: HoldingsReport; commodities: Commodities } = $props();

  const POLL_INTERVAL_MS = 45_000;
  const SPARKLINE_POINTS = 20;
  const SPARKLINE_WIDTH = 60;
  const SPARKLINE_HEIGHT = 20;

  const priced_holdings = $derived(
    holdingsReport.holdings.filter((h) => h.cost_currency != null),
  );
  const tickers = $derived(priced_holdings.map((h) => h.currency));
  const total_market_value = $derived(
    priced_holdings.reduce((sum, h) => sum + (h.market_value ?? 0), 0),
  );
  const totals_currency = $derived(
    priced_holdings.find((h) => h.cost_currency != null)?.cost_currency ?? "",
  );

  let live: Record<string, Quote> = $state({});
  let live_enabled = $state(true);

  async function poll(): Promise<void> {
    if (!live_enabled || tickers.length === 0) {
      return;
    }
    try {
      live = await get_live_prices({ tickers: tickers.join(",") });
    } catch {
      // Live prices are optional - a failed poll just leaves the last
      // known values (or the beancount-recorded price) in place.
    }
  }

  onMount(() => {
    void poll();
    const id = setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);
    return () => {
      clearInterval(id);
    };
  });

  function toggle_live(): void {
    live_enabled = !live_enabled;
    if (live_enabled) {
      void poll();
    } else {
      live = {};
    }
  }

  function average_cost(
    book_value: number | null,
    units: number,
  ): number | null {
    return book_value != null && units !== 0 ? book_value / units : null;
  }

  function profit_loss(
    market_value: number | null,
    book_value: number | null,
  ): number | null {
    return market_value != null && book_value != null
      ? market_value - book_value
      : null;
  }

  function sparkline_points(
    currency: string,
    cost_currency: string,
  ): string | null {
    const series = commodities.find(
      (c) => c.base === currency && c.quote === cost_currency,
    );
    if (series == null || series.prices.length < 2) {
      return null;
    }
    const values = series.prices
      .slice(-SPARKLINE_POINTS)
      .map(([, price]) => price);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const step = SPARKLINE_WIDTH / (values.length - 1);
    return values
      .map((v, i) => {
        const x = i * step;
        const y = SPARKLINE_HEIGHT - ((v - min) / range) * SPARKLINE_HEIGHT;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }
</script>

{#if priced_holdings.length}
  <div class="card holdings-preview">
    <div class="holdings-header">
      <div>
        <div class="card-label">{_("Holdings")}</div>
        <div class="stat-muted holdings-subtitle">
          {_("cost basis from beancount lots · marks streaming")}
        </div>
      </div>
      <button type="button" class="live-toggle" onclick={toggle_live}>
        {live_enabled ? _("Live") : _("Live marks off")}
      </button>
    </div>
    <table>
      <thead>
        <tr>
          <th>{_("Ticker")}</th>
          <th>{_("Units · basis")}</th>
          <th>{_("Last")}</th>
          <th>{_("Day")}</th>
          <th></th>
          <th>{_("P/L")}</th>
        </tr>
      </thead>
      <tbody>
        {#each priced_holdings as holding (holding.currency)}
          {@const cost_currency = holding.cost_currency}
          {@const quote = live[holding.currency]}
          {@const price = quote?.price ?? holding.price}
          {@const name = $ledgerData.currency_names[holding.currency]}
          {@const avg_cost = average_cost(holding.book_value, holding.units)}
          {@const pl = profit_loss(holding.market_value, holding.book_value)}
          {@const points =
            cost_currency != null
              ? sparkline_points(holding.currency, cost_currency)
              : null}
          <tr>
            <td class="holdings-ticker">
              <div>{holding.currency}</div>
              {#if name != null}
                <div class="stat-muted holdings-name">{name}</div>
              {/if}
            </td>
            <td class="num">
              <div>{$ctx.num(holding.units, holding.currency)}</div>
              <div class="stat-muted">
                {avg_cost != null && cost_currency != null
                  ? `@ ${$ctx.amount(avg_cost, cost_currency)}`
                  : "—"}
              </div>
            </td>
            <td class="num" class:holdings-price-live={quote != null}>
              {price != null && cost_currency != null
                ? $ctx.amount(price, cost_currency)
                : "—"}
            </td>
            <td
              class="num"
              class:stat-positive={quote != null && quote.day_change_pct >= 0}
              class:stat-negative={quote != null && quote.day_change_pct < 0}
            >
              {quote != null
                ? $ctx.percentage(quote.day_change_pct / 100)
                : "—"}
            </td>
            <td class="holdings-sparkline">
              {#if points != null}
                <svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}">
                  <polyline {points}></polyline>
                </svg>
              {/if}
            </td>
            <td
              class="num"
              class:stat-positive={pl != null && pl >= 0}
              class:stat-negative={pl != null && pl < 0}
            >
              <div>
                {pl != null && cost_currency != null
                  ? $ctx.amount(pl, cost_currency)
                  : "—"}
              </div>
              <div class="holdings-pl-pct">
                {$ctx.percentage(holding.unrealized_profit_pct / 100)}
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    <div class="holdings-footer">
      <span class="stat-muted">
        {format(_("%(positions)s positions · %(accounts)s accounts"), {
          positions: priced_holdings.length.toString(),
          accounts: holdingsReport.account_count.toString(),
        })}
      </span>
      <span>
        {format(_("market value %(value)s"), {
          value: $ctx.amount(total_market_value, totals_currency),
        })}
      </span>
    </div>
  </div>
{/if}

<style>
  .holdings-preview {
    grid-column: 1 / -1;
  }

  .holdings-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 0.5em;
  }

  .holdings-subtitle {
    margin-top: 0.2em;
    font-size: 0.8em;
  }

  .live-toggle {
    padding: 0.2em 0.6em;
    font-size: 0.75em;
    color: var(--text-color-lightest);
    cursor: pointer;
    background: none;
    border: 1px solid var(--border);
    border-radius: 10px;
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

  th:first-child,
  td.holdings-ticker {
    text-align: left;
  }

  td {
    padding: 0.4em 0.5em;
    vertical-align: top;
    text-align: right;
    border-top: 1px solid var(--border);
  }

  td.holdings-ticker {
    font-weight: 600;
  }

  .holdings-name {
    font-size: 0.8em;
    font-weight: 400;
  }

  .holdings-price-live {
    color: var(--text-color);
  }

  .holdings-pl-pct {
    font-size: 0.85em;
    opacity: 0.8;
  }

  .holdings-sparkline svg {
    width: 60px;
    height: 20px;
    overflow: visible;
  }

  .holdings-sparkline polyline {
    fill: none;
    stroke: var(--accent-forecast);
    stroke-width: 1.5;
  }

  .holdings-footer {
    display: flex;
    justify-content: space-between;
    padding-top: 0.6em;
    margin-top: 0.3em;
    font-family: var(--font-family-monospaced);
    font-size: 0.85em;
    border-top: 1px solid var(--border);
  }
</style>
