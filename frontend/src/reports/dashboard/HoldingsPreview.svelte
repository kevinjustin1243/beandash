<script lang="ts">
  import { onMount } from "svelte";

  import { get_live_prices } from "../../api/index.ts";
  import type { Commodities, Holding, Quote } from "../../api/validators.ts";
  import { _ } from "../../i18n.ts";
  import { ctx } from "../../stores/format.ts";

  let {
    holdings,
    commodities,
  }: { holdings: Holding[]; commodities: Commodities } = $props();

  const POLL_INTERVAL_MS = 45_000;
  const SPARKLINE_POINTS = 20;
  const SPARKLINE_WIDTH = 60;
  const SPARKLINE_HEIGHT = 20;

  const priced_holdings = $derived(
    holdings.filter((h) => h.cost_currency != null),
  );
  const tickers = $derived(priced_holdings.map((h) => h.currency));

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
      <div class="card-label">{_("Holdings")}</div>
      <button type="button" class="live-toggle" onclick={toggle_live}>
        {live_enabled ? _("Live: on") : _("Live: off")}
      </button>
    </div>
    <table>
      <thead>
        <tr>
          <th>{_("Ticker")}</th>
          <th>{_("Units")}</th>
          <th>{_("Price")}</th>
          <th>{_("Day")}</th>
          <th></th>
          <th>{_("Market value")}</th>
          <th>{_("Unrealized")}</th>
        </tr>
      </thead>
      <tbody>
        {#each priced_holdings as holding (holding.currency)}
          {@const cost_currency = holding.cost_currency}
          {@const quote = live[holding.currency]}
          {@const price = quote?.price ?? holding.price}
          {@const points =
            cost_currency != null
              ? sparkline_points(holding.currency, cost_currency)
              : null}
          <tr>
            <td class="holdings-ticker">{holding.currency}</td>
            <td class="num">{$ctx.num(holding.units, holding.currency)}</td>
            <td class="num">
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
                  <polyline points={points}></polyline>
                </svg>
              {/if}
            </td>
            <td class="num">
              {holding.market_value != null && cost_currency != null
                ? $ctx.amount(holding.market_value, cost_currency)
                : "—"}
            </td>
            <td
              class="num"
              class:stat-positive={holding.unrealized_profit_pct >= 0}
              class:stat-negative={holding.unrealized_profit_pct < 0}
            >
              {$ctx.percentage(holding.unrealized_profit_pct / 100)}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .holdings-preview {
    grid-column: 1 / -1;
  }

  .holdings-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5em;
  }

  .live-toggle {
    padding: 0.2em 0.6em;
    font-size: 0.75em;
    color: var(--text-color-lightest);
    background: none;
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
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
    padding: 0.3em 0.5em;
    text-align: right;
    border-top: 1px solid var(--border);
  }

  td.holdings-ticker {
    font-weight: 600;
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
</style>
