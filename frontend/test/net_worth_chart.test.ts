import { deepEqual, equal, ok } from "node:assert/strict";
import { test } from "node:test";

import { ParsedLineChart } from "../src/charts/line.ts";
import {
  build_net_worth_chart_geometry,
  extract_net_worth_series,
} from "../src/reports/dashboard/net_worth_chart.ts";

const d1 = new Date("2020-01-01");
const d2 = new Date("2020-02-01");
const d3 = new Date("2020-03-01");
const d4 = new Date("2020-04-01");

const chart = new ParsedLineChart("Net Worth", [
  { date: d1, balance: { USD: 100 } },
  { date: d2, balance: { USD: 200 } },
  { date: d3, balance: { USD: 300 } },
  { date: d3, balance: { "USD (projected)": 300 } },
  {
    date: d4,
    balance: {
      "USD (projected)": 400,
      "USD (projected high)": 450,
      "USD (projected low)": 350,
    },
  },
]);

test("extract net worth series from chart data", () => {
  const series = extract_net_worth_series([chart], "USD");
  deepEqual(
    series.historic.map((p) => p.value),
    [100, 200, 300],
  );
  deepEqual(
    series.forecast.map((p) => p.value),
    [300, 400],
  );
  // The anchor point (first forecast point) has no recorded band yet, so
  // it collapses to the projected value itself rather than a gap.
  deepEqual(
    series.band_high.map((p) => p.value),
    [300, 450],
  );
  deepEqual(
    series.band_low.map((p) => p.value),
    [300, 350],
  );
});

test("extract net worth series when there is no line chart", () => {
  const series = extract_net_worth_series([], "USD");
  deepEqual(series, {
    historic: [],
    forecast: [],
    band_high: [],
    band_low: [],
  });
});

test("net worth chart geometry needs at least two historic points", () => {
  equal(
    build_net_worth_chart_geometry({
      historic: [{ date: d1, value: 100 }],
      forecast: [],
      band_high: [],
      band_low: [],
    }),
    null,
  );
});

test("net worth chart geometry builds line, area, forecast, and band paths", () => {
  const series = extract_net_worth_series([chart], "USD");
  const geometry = build_net_worth_chart_geometry(series);
  ok(geometry);

  const total_span = d4.getTime() - d1.getTime();
  const expected_split_x = ((d3.getTime() - d1.getTime()) / total_span) * 900;

  equal(geometry.line_path.startsWith("M0.0"), true);
  equal(geometry.line_path.split("L").length, 3); // 3 historic points: 1 M + 2 L
  equal(geometry.area_path.endsWith("Z"), true);
  ok(geometry.forecast_path.length > 0);
  ok(geometry.band_path.endsWith(" Z"));
  ok(Math.abs(geometry.split_x - expected_split_x) < 0.1);
  ok(geometry.axis_start.length > 0);
  ok(geometry.axis_mid.length > 0);
  ok(geometry.axis_end.length > 0);
});

test("net worth chart geometry with no forecast data", () => {
  const geometry = build_net_worth_chart_geometry({
    historic: [
      { date: d1, value: 100 },
      { date: d2, value: 200 },
    ],
    forecast: [],
    band_high: [],
    band_low: [],
  });
  ok(geometry);
  equal(geometry.forecast_path, "");
  equal(geometry.band_path, "");
});
