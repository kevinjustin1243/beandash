import { account_hierarchy_validator } from "../charts/hierarchy.ts";
import { charts_validator } from "../charts/index.ts";
import { entryValidator } from "../entries/index.ts";
import type { ValidationT } from "../lib/validation.ts";
import {
  array,
  boolean,
  constants,
  date,
  number,
  object,
  optional,
  record,
  string,
  tuple,
} from "../lib/validation.ts";
/** A Beancount error that should be shown to the user in the list of errors. */
export interface BeancountError {
  readonly type: string;
  readonly message: string;
  readonly source: {
    readonly filename: string;
    readonly lineno: number;
  } | null;
}

/** Validator for a BeancountError. */
export const error_validator = object<BeancountError>({
  type: string,
  message: string,
  source: optional(object({ filename: string, lineno: number })),
});

/** A flagged unusual transaction or newly-seen payee. */
export interface Insight {
  readonly type: "new_payee" | "unusual_transaction";
  readonly payee: string;
  readonly title: string;
  readonly detail: string;
  readonly value: string;
  readonly tone: string;
  readonly entry_hash: string;
}

/** Validator for an Insight. */
export const insight_validator = object<Insight>({
  type: constants("new_payee", "unusual_transaction"),
  payee: string,
  title: string,
  detail: string,
  value: string,
  tone: string,
  entry_hash: string,
});

/** Validator for the details for a single account. */
const account_detail = object({
  balance_string: optional(string),
  close_date: optional(date),
  last_entry: optional(object({ date, entry_hash: string })),
  uptodate_status: optional(constants("green", "yellow", "red")),
});
const account_details = record(account_detail);

export type AccountDetail = ValidationT<typeof account_detail>;

/** Validator for the Fava options that are used in the frontend. */
const fava_options = object({
  auto_reload: boolean,
  currency_column: number,
  conversion_currencies: array(string),
  collapse_pattern: array(string),
  indent: number,
  invert_gains_losses_colors: boolean,
  invert_income_liabilities_equity: boolean,
  show_closed_accounts: boolean,
  show_accounts_with_zero_balance: boolean,
  show_accounts_with_zero_transactions: boolean,
  locale: optional(string),
  uptodate_indicator_grey_lookback_days: number,
  insert_entry: array(
    object({ date: string, filename: string, lineno: number, re: string }),
  ),
});

/** Validator for the Beancount options that are used in the frontend. */
const options = object({
  documents: array(string),
  filename: string,
  include: array(string),
  name_assets: string,
  name_equity: string,
  name_expenses: string,
  name_income: string,
  name_liabilities: string,
  operating_currency: array(string),
  title: string,
});

const extensions = array(
  object({
    name: string,
    report_title: optional(string),
    has_js_module: boolean,
  }),
);

export const ledgerDataValidator = object({
  account_details,
  accounts: array(string),
  base_url: string,
  currencies: array(string),
  currency_names: record(string),
  entries_count: number,
  errors: array(error_validator),
  extensions,
  fava_options,
  have_excel: boolean,
  incognito: boolean,
  links: array(string),
  options,
  other_ledgers: array(tuple(string, string)),
  payees: array(string),
  precisions: record(number),
  sidebar_links: array(tuple(string, string)),
  tags: array(string),
  user_queries: array(object({ name: string, query_string: string })),
  years: array(string),
});

export type LedgerData = ValidationT<typeof ledgerDataValidator>;

const date_range = object({ begin: date, end: date });

export const commodities_validator = array(
  object({ base: string, quote: string, prices: array(tuple(date, number)) }),
);

export type Commodities = ValidationT<typeof commodities_validator>;

export const context_validator = object({
  entry: entryValidator,
  balances_before: optional(record(array(string))),
  balances_after: optional(record(array(string))),
});

const account_budget = object({
  budget: record(number),
  budget_children: record(number),
});
export type AccountBudget = ValidationT<typeof account_budget>;

export const tree_report_validator = object({
  charts: charts_validator,
  trees: array(account_hierarchy_validator),
  date_range: optional(date_range),
});

export const allocation_entry_validator = object({
  account: string,
  name: string,
  balance: number,
  pct: number,
});

export type AllocationEntry = ValidationT<typeof allocation_entry_validator>;

export const dashboard_validator = object({
  charts: charts_validator,
  date_range: optional(date_range),
  currency: string,
  unrealized_gain: optional(number),
  allocation: array(allocation_entry_validator),
  liquid_cash: number,
});

export const predictions_validator = object({
  currency: string,
  net_worth: number,
  net_worth_projected: number,
  net_worth_r_squared: number,
  net_worth_monthly_change: optional(number),
  savings_rate: optional(number),
  spend_next_period: optional(number),
  spend_trailing_monthly: number,
  cash_flow_90d: optional(number),
  fi_target: number,
  fi_years: optional(number),
});

export type Predictions = ValidationT<typeof predictions_validator>;

export const goal_progress_validator = object({
  account: string,
  label: string,
  target: number,
  currency: string,
  target_date: optional(date),
  balance: number,
  pct_complete: optional(number),
  is_payoff: boolean,
  eta_years: optional(number),
  on_track: optional(boolean),
});

export type GoalProgress = ValidationT<typeof goal_progress_validator>;

export const uncategorized_transaction_validator = optional(
  object({
    entry: entryValidator,
    entry_hash: string,
    placeholder_account: string,
    suggestions: array(tuple(string, number)),
  }),
);

export type UncategorizedTransaction = ValidationT<
  typeof uncategorized_transaction_validator
>;

export const holding_validator = object({
  currency: string,
  cost_currency: optional(string),
  units: number,
  price: optional(number),
  book_value: optional(number),
  market_value: optional(number),
  unrealized_profit_pct: number,
});

export type Holding = ValidationT<typeof holding_validator>;

export const holdings_report_validator = object({
  holdings: array(holding_validator),
  account_count: number,
});

export type HoldingsReport = ValidationT<typeof holdings_report_validator>;

export const quote_validator = object({
  price: number,
  day_change_pct: number,
  as_of: number,
});

export type Quote = ValidationT<typeof quote_validator>;

export const live_prices_validator = record(quote_validator);

export const account_report_validator = object({
  charts: charts_validator,
  journal: optional(string),
  dates: optional(array(date_range)),
  interval_balances: optional(array(account_hierarchy_validator)),
  budgets: optional(record(array(account_budget))),
});

export const options_validator = object({
  fava_options: record(string),
  beancount_options: record(string),
});
