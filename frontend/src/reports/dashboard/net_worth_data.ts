import {
  get_commodities,
  get_dashboard,
  get_predictions,
} from "../../api/index.ts";
import type { Commodities, Predictions } from "../../api/validators.ts";
import type { ParsedFavaChart } from "../../charts/index.ts";
import { ParsedLineChart } from "../../charts/line.ts";
import type { FiltersConversionInterval } from "../../stores/filters.ts";

export interface NetWorthHeroData {
  charts: ParsedFavaChart[];
  date_range: { begin: Date; end: Date } | null;
  currency: string;
  unrealizedGain: number | null;
  netWorth: number | null;
  netWorthChange: number | null;
  predictions: Predictions;
  commodities: Commodities;
}

/**
 * Current net worth and the change from the previous historic data point,
 * for the given currency - read directly off the (already-fetched) Net
 * Worth chart rather than a separate request. Only actual historic points
 * are considered (not the forecast/band series appended to the same chart).
 */
function net_worth_and_change(
  charts: readonly ParsedFavaChart[],
  currency: string,
): { netWorth: number | null; netWorthChange: number | null } {
  // get_dashboard() always puts the Net Worth chart first.
  const net_worth_chart = charts[0];
  const historic = (
    net_worth_chart instanceof ParsedLineChart ? net_worth_chart.data : []
  ).filter((d) => d.balance[currency] !== undefined);
  const last = historic.at(-1);
  const previous = historic.at(-2);
  return {
    netWorth: last ? (last.balance[currency] ?? null) : null,
    netWorthChange:
      last && previous
        ? (last.balance[currency] ?? 0) - (previous.balance[currency] ?? 0)
        : null,
  };
}

/** Load the net worth hero data (stats + chart), shared by the Overview and Net worth reports. */
export async function load_net_worth_hero(
  filters: FiltersConversionInterval,
): Promise<NetWorthHeroData> {
  const [report, commodities, predictions] = await Promise.all([
    get_dashboard(filters),
    get_commodities(filters),
    get_predictions(filters),
  ]);
  const { netWorth, netWorthChange } = net_worth_and_change(
    report.charts,
    report.currency,
  );
  return {
    charts: report.charts,
    date_range: report.date_range,
    currency: report.currency,
    unrealizedGain: report.unrealized_gain,
    netWorth,
    netWorthChange,
    predictions,
    commodities,
  };
}
