import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import type { NetWorthHeroData } from "../dashboard/net_worth_data.ts";
import { load_net_worth_hero } from "../dashboard/net_worth_data.ts";
import { Route } from "../route.ts";
import NetWorth from "./NetWorth.svelte";

export type NetWorthReportProps = NetWorthHeroData;

export const net_worth = new Route<NetWorthReportProps>(
  "net_worth",
  NetWorth,
  async (url) => load_net_worth_hero(getURLFilters(url)),
  () => _("Net worth"),
);
