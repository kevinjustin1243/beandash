import { get_goals } from "../../api/index.ts";
import type { GoalProgress } from "../../api/validators.ts";
import { _ } from "../../i18n.ts";
import { Route } from "../route.ts";
import Goals from "./Goals.svelte";

export interface GoalsReportProps {
  goals: GoalProgress[];
}

export const goals = new Route<GoalsReportProps>(
  "goals",
  Goals,
  async () => ({ goals: await get_goals() }),
  () => _("Goals"),
);
