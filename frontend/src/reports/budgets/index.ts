import { get_budgets } from "../../api/index.ts";
import type { BudgetReport } from "../../api/validators.ts";
import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import { Route } from "../route.ts";
import Budgets from "./Budgets.svelte";

export interface BudgetsReportProps {
  report: BudgetReport;
}

export const budgets = new Route<BudgetsReportProps>(
  "budgets",
  Budgets,
  async (url) => ({ report: await get_budgets(getURLFilters(url)) }),
  () => _("Budgets"),
);
