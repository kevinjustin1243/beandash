import type { ParsedFavaChart } from "../../charts/index.ts";
import { ParsedLineChart } from "../../charts/line.ts";

const PROJECTED_SUFFIX = " (projected)";
const PROJECTED_HIGH_SUFFIX = " (projected high)";
const PROJECTED_LOW_SUFFIX = " (projected low)";

const CHART_WIDTH = 900;
const CHART_HEIGHT = 240;

interface DateValue {
  date: Date;
  value: number;
}

export interface NetWorthChartSeries {
  historic: DateValue[];
  forecast: DateValue[];
  band_high: DateValue[];
  band_low: DateValue[];
}

/**
 * Pull the actual/forecast/band series for one currency out of the (already
 * fetched) Net Worth chart's data - the backend appends the forecast and
 * its confidence band to the same chart as extra currency-suffixed keys on
 * each point (see `PROJECTED_SUFFIX` and friends in `core/forecast.py`), so
 * this is purely a client-side reshape, not a new data source.
 */
export function extract_net_worth_series(
  charts: readonly ParsedFavaChart[],
  currency: string,
): NetWorthChartSeries {
  // get_dashboard() always puts the Net Worth chart first.
  const chart = charts[0];
  const data = chart instanceof ParsedLineChart ? chart.data : [];
  const projected_key = `${currency}${PROJECTED_SUFFIX}`;
  const high_key = `${currency}${PROJECTED_HIGH_SUFFIX}`;
  const low_key = `${currency}${PROJECTED_LOW_SUFFIX}`;

  const historic: DateValue[] = [];
  const forecast: DateValue[] = [];
  const band_high: DateValue[] = [];
  const band_low: DateValue[] = [];
  for (const { date, balance } of data) {
    const actual = balance[currency];
    if (actual !== undefined) {
      historic.push({ date, value: actual });
    }
    const projected = balance[projected_key];
    if (projected !== undefined) {
      forecast.push({ date, value: projected });
      // The anchor point (where the forecast starts) has no band yet - it
      // collapses to the projected value itself, giving a zero-width band
      // there instead of a gap.
      band_high.push({ date, value: balance[high_key] ?? projected });
      band_low.push({ date, value: balance[low_key] ?? projected });
    }
  }
  return { historic, forecast, band_high, band_low };
}

export interface NetWorthChartGeometry {
  line_path: string;
  area_path: string;
  forecast_path: string;
  band_path: string;
  split_x: number;
  axis_start: string;
  axis_mid: string;
  axis_end: string;
}

const axis_date_format = new Intl.DateTimeFormat(undefined, {
  month: "short",
  year: "2-digit",
});

function path(points: readonly [number, number][]): string {
  return points
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");
}

/**
 * Build the SVG path geometry for the net worth chart: an actual line
 * (with a soft area fill), a dashed forecast continuation, and a shaded
 * confidence band - scaled into a fixed `CHART_WIDTH` x `CHART_HEIGHT`
 * viewBox positioned by real dates (not by index), so uneven point spacing
 * doesn't distort it.
 */
export function build_net_worth_chart_geometry(
  series: NetWorthChartSeries,
): NetWorthChartGeometry | null {
  const { historic, forecast, band_high, band_low } = series;
  if (historic.length < 2) {
    return null;
  }

  const all_points = [...historic, ...forecast, ...band_high, ...band_low];
  const dates = all_points.map((p) => p.date.getTime());
  const values = all_points.map((p) => p.value);
  const min_date = Math.min(...dates);
  const max_date = Math.max(...dates);
  const date_span = max_date - min_date || 1;
  const min_value = Math.min(...values);
  const max_value = Math.max(...values);
  const lo = min_value - Math.abs(min_value) * 0.04;
  const hi = max_value + Math.abs(max_value) * 0.02;
  const value_span = hi - lo || 1;

  const x = (d: Date) => ((d.getTime() - min_date) / date_span) * CHART_WIDTH;
  const y = (v: number) =>
    CHART_HEIGHT - ((v - lo) / value_span) * CHART_HEIGHT;
  const xy = (points: readonly DateValue[]): [number, number][] =>
    points.map((p): [number, number] => [x(p.date), y(p.value)]);

  const last_historic = historic[historic.length - 1];
  if (!last_historic) {
    return null;
  }
  const line_path = path(xy(historic));
  const chart_height = CHART_HEIGHT.toString();
  const area_path = `${line_path} L${x(last_historic.date).toFixed(1)} ${chart_height} L0 ${chart_height} Z`;
  const forecast_path = forecast.length ? path(xy(forecast)) : "";
  const band_path = band_high.length
    ? `${path([...xy(band_high), ...xy(band_low).reverse()])} Z`
    : "";

  const last_forecast = forecast[forecast.length - 1];
  const mid_historic = historic[Math.floor(historic.length / 2)];

  return {
    line_path,
    area_path,
    forecast_path,
    band_path,
    split_x: x(last_historic.date),
    axis_start: axis_date_format.format(
      historic[0]?.date ?? last_historic.date,
    ),
    axis_mid: axis_date_format.format(mid_historic?.date ?? last_historic.date),
    axis_end: axis_date_format.format((last_forecast ?? last_historic).date),
  };
}

export const NET_WORTH_CHART_WIDTH = CHART_WIDTH;
export const NET_WORTH_CHART_HEIGHT = CHART_HEIGHT;
