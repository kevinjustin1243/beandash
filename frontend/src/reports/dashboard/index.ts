import {
  get_holdings,
  get_insights,
  get_uncategorized_transaction,
} from "../../api/index.ts";
import type {
  Commodities,
  Holding,
  Insight,
  Predictions,
  UncategorizedTransaction,
} from "../../api/validators.ts";
import type { ParsedFavaChart } from "../../charts/index.ts";
import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import { Route } from "../route.ts";
import Dashboard from "./Dashboard.svelte";
import { load_net_worth_hero } from "./net_worth_data.ts";

export interface DashboardReportProps {
  charts: ParsedFavaChart[];
  date_range: { begin: Date; end: Date } | null;
  currency: string;
  unrealizedGain: number | null;
  netWorth: number | null;
  netWorthChange: number | null;
  insights: Insight[];
  predictions: Predictions;
  uncategorized: UncategorizedTransaction;
  holdings: Holding[];
  commodities: Commodities;
}

export const dashboard = new Route<DashboardReportProps>(
  "dashboard",
  Dashboard,
  async (url) => {
    const filters = getURLFilters(url);
    const [hero, insights, uncategorized, holdings] = await Promise.all([
      load_net_worth_hero(filters),
      get_insights(filters),
      get_uncategorized_transaction(),
      get_holdings(filters),
    ]);
    return {
      ...hero,
      insights,
      uncategorized,
      holdings,
    };
  },
  () => _("Dashboard"),
);
