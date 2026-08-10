import { get_dashboard, get_predictions } from "../../api/index.ts";
import type { Predictions } from "../../api/validators.ts";
import type { ParsedFavaChart } from "../../charts/index.ts";
import { _ } from "../../i18n.ts";
import { getURLFilters } from "../../stores/filters.ts";
import { Route } from "../route.ts";
import PredictionsReport from "./PredictionsReport.svelte";

export interface PredictionsReportProps {
  predictions: Predictions;
  charts: ParsedFavaChart[];
  currency: string;
}

export const predictions = new Route<PredictionsReportProps>(
  "predictions",
  PredictionsReport,
  async (url) => {
    const filters = getURLFilters(url);
    const [report, predictions_data] = await Promise.all([
      get_dashboard(filters),
      get_predictions(filters),
    ]);
    return {
      predictions: predictions_data,
      charts: report.charts,
      currency: report.currency,
    };
  },
  () => _("Predictions"),
);
