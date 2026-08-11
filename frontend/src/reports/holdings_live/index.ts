import { get_commodities, get_holdings } from "../../api/index.ts";
import type { Commodities, HoldingsReport } from "../../api/validators.ts";
import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import { Route } from "../route.ts";
import HoldingsLive from "./HoldingsLive.svelte";

export interface HoldingsLiveReportProps {
  holdingsReport: HoldingsReport;
  commodities: Commodities;
}

export const holdings_live = new Route<HoldingsLiveReportProps>(
  "holdings_live",
  HoldingsLive,
  async (url) => {
    const filters = getURLFilters(url);
    const [holdingsReport, commodities] = await Promise.all([
      get_holdings(filters),
      get_commodities(filters),
    ]);
    return { holdingsReport, commodities };
  },
  () => _("Holdings"),
);
