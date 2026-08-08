import { get_commodities, get_holdings } from "../../api/index.ts";
import type { Commodities, Holding } from "../../api/validators.ts";
import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import { Route } from "../route.ts";
import HoldingsLive from "./HoldingsLive.svelte";

export interface HoldingsLiveReportProps {
  holdings: Holding[];
  commodities: Commodities;
}

export const holdings_live = new Route<HoldingsLiveReportProps>(
  "holdings_live",
  HoldingsLive,
  async (url) => {
    const filters = getURLFilters(url);
    const [holdings, commodities] = await Promise.all([
      get_holdings(filters),
      get_commodities(filters),
    ]);
    return { holdings, commodities };
  },
  () => _("Holdings"),
);
