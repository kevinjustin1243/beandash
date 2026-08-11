import { account_report } from "./accounts/index.ts";
import { dashboard } from "./dashboard/index.ts";
import { errors } from "./errors/index.ts";
import { goals } from "./goals/index.ts";
import { holdings_live } from "./holdings_live/index.ts";
import { journal } from "./journal/index.ts";
import { net_worth } from "./net_worth/index.ts";
import { options } from "./options/index.ts";
import { predictions } from "./predictions/index.ts";
import { query } from "./query/index.ts";
import type { FrontendRoute } from "./route.ts";
import {
  balance_sheet,
  income_statement,
  trial_balance,
} from "./tree_reports/index.ts";

/**
 * This is a list of routes to render in the frontend. For those that we render
 * in the frontend, the router will pre-load any required data with the load
 * function and then render the component. These components hence need to be
 * able to react to changed data (using idiomatic Svelte code should ensure
 * that, care mainly needs to be taken around lifecycle hooks that should run
 * if some parts of the data change)
 */
export const frontend_routes: FrontendRoute[] = [
  account_report,
  balance_sheet,
  dashboard,
  errors,
  goals,
  holdings_live,
  income_statement,
  journal,
  net_worth,
  options,
  predictions,
  query,
  trial_balance,
];
