# Beandash: fava fork — phased feature plan

## Status

Phases 1–10 done and pushed to `main`. Part 2 of the plan is complete.

| Phase | Status |
| --- | --- |
| 1 — Remove Import/Editor reports | ✅ Done |
| 2 — Dashboard report (net worth/allocation/performance) | ✅ Done |
| 3 — Auto-categorization suggester | ✅ Done |
| 4 — Forecasting / projections | ✅ Done |
| 5 — Anomaly / insight detection | ✅ Done |
| 6 — Dark theme & typography | ✅ Done |
| 7 — Predictions engine backend upgrades | ✅ Done |
| 8 — Overview page rebuild (frontend) | ✅ Done |
| 9 — Live stock prices (Finnhub) | ✅ Done |
| 10 — Dedicated pages + sidebar restructure | ✅ Done |

## Context

This repo is a working fork of Fava (the Beancount web UI), used as a personal single-user
dashboard against one `main.beancount` file (with includes). The goal is to make it a more
intuitive personal-finance tool: better net worth / stock visualizations, plus some ML/AI
assistance (auto-categorization, forecasting, anomaly detection). Design/styling will be
handled separately later — this plan is about features and architecture, not visuals.

Scope decisions already made with the user:
- Single user, single ledger tree (no multi-ledger switching needed).
- Keep: Journal/account pages, BQL query console, Balance Sheet, Income Statement, Trial Balance.
- Drop: the Import report and the in-browser full-file Editor report (not used).
- ML wanted: auto-categorization, forecasting/projection, anomaly/insight detection. Not NL query.

Codebase research (already done, informs every phase below):
- Reports register in two places that must stay in sync: `src/fava/application.py`
  (`CLIENT_SIDE_REPORTS` list gates the Flask catch-all route) and
  `frontend/src/reports/routes.ts` (`frontend_routes` array, each a `Route`/`DatalessRoute`
  from `frontend/src/reports/route.ts`). Nav links live in
  `frontend/src/sidebar/AsideContents.svelte`.
- Chart data is already computed server-side and is directly reusable:
  `ChartModule` in `src/fava/core/charts.py` (`net_worth`, `hierarchy`, `interval_totals`,
  `linechart`), wrapped into tagged dataclasses by `ChartApi` in `src/fava/internal_api.py`
  (`ChartApi.net_worth()`, `.hierarchy()`, etc.). `get_commodities()` in `json_api.py` returns
  full historical price series per commodity pair (beancount price directives are tracked, not
  just point-in-time balances). Holdings return-% is already computed via BQL in
  `frontend/src/reports/holdings/index.ts` (`unrealized_profit_pct`) — same query pattern is
  reusable for a time-series version.
- Frontend chart building blocks: `frontend/src/charts/` (`LineChart.svelte`,
  `Treemap.svelte`, `ChartSwitcher.svelte`, `context.ts`). Best template for "backend series →
  chart" is `frontend/src/reports/commodities/index.ts` (calls `get_commodities()`, maps to
  `LineChart` client-side).
- Backend modules are plain `FavaModule` subclasses (`src/fava/core/module_base.py`), manually
  wired into `FavaLedger.__init__`/`load_file()` (`src/fava/core/__init__.py`) — no dynamic
  registry. `AttributesModule` (`src/fava/core/attributes.py`) + `ExponentialDecayRanker`
  (`src/fava/util/ranking.py`) is the closest existing analog for the categorization feature.
  Everything is request-driven; there is no scheduler/background-job mechanism in this codebase
  — a "monthly digest" should be computed on-demand when the dashboard loads, not pushed.
- API endpoints follow the `@api_endpoint` decorator pattern in `src/fava/json_api.py` (method
  inferred from function name prefix, return value auto-wrapped). `get_payee_accounts` is the
  template for a trivial ledger-module passthrough endpoint.
- No numerical/ML dependency exists yet (no numpy/scikit-learn/pandas). `requires-python >=3.10`.
  Given personal-finance data volumes (thousands, not millions, of rows), hand-rolled stats
  (linear trend, z-score) avoids adding a heavy dependency; only add one if a phase genuinely
  needs it.
- Import/Editor removal mapping (from full-repo trace) — see Phase 1 for the precise file list,
  including two important non-obvious keepers: the Journal's entry-context modal reuses
  `frontend/src/editor/SliceEditor.svelte` + the slice API endpoints (`get_source_slice`-family
  in `file.py`), and the BQL query editor reuses `frontend/src/codemirror/*`. Neither is part of
  the Editor *report* being removed.

---

## Phase 1 — Remove Import and Editor reports

**Status: ✅ Done**

**Goal:** shrink backend/frontend surface before adding new features, without breaking Journal,
BQL, or the entry-context ("jump to source") modal, which share code with these reports.

**Delete (Import):**
- `frontend/src/reports/import/` (entire dir: `Extract.svelte`, `FileList.svelte`,
  `Import.svelte`, `ImportFileUpload.svelte`, `index.ts`)
- `src/fava/core/ingest.py` (whole module)
- `json_api.py`: `get_extract`, `get_imports`, `put_upload_import_file`
- `fava_options.py`: `import_config`, `import_dirs`/`set_import_dirs` — but check
  `is_document_or_import_file` in `core/documents.py` first; trim its `import_dirs` check
  rather than breaking the generic document-download route
- Tests: `tests/test_core_ingest.py`, related `__snapshots__` files, `tests/data/import*`,
  and `test_api_upload_import_file`/`test_api_imports` in `tests/test_json_api.py`
- `src/fava/help/import.md`
- Registrations: remove `"import"` from `CLIENT_SIDE_REPORTS` (`application.py`), remove from
  `frontend_routes` (`routes.ts`) and the nav link in `AsideContents.svelte`; drop
  `import_config` from `frontend/src/stores/fava_options.ts` and `api/validators.ts`

**Delete (Editor report only — not the shared editor machinery):**
- `frontend/src/reports/editor/` (entire dir)
- `frontend/src/lib/sources.ts`
- `frontend/src/codemirror/beancount-format.ts`
- `json_api.py`: `get_source`, `put_source`, `put_format_source`
- `FileModule.get_source`/`set_source` in `core/file.py` (keep `get_entry_slice`/
  `save_entry_slice`/`delete_entry_slice` — used by the Journal context modal)
- `fava_options.py`: `use_external_editor`, `default_file`/`set_default_file`
- Tests: the non-slice source/format tests in `tests/test_json_api.py` (keep the
  `*_slice_*` tests)
- Registrations: remove `"editor"` from `CLIENT_SIDE_REPORTS`, from `routes.ts`, and its nav link

**Do NOT touch** (shared with Journal/Context modal or BQL query, confirmed by trace):
`frontend/src/editor/SliceEditor.svelte`, `SaveButton.svelte`, `DeleteButton.svelte`,
`DocumentPreviewEditor.svelte`; all of `frontend/src/codemirror/` except
`beancount-format.ts`; `frontend/css/editor.css`; `frontend/src/stores/editor.ts`;
`core/file.py` module itself; `core/documents.py`.

**Known loose end to fix in this phase:** `frontend/src/helpers.ts::urlForSource` builds a
link to the now-deleted `editor/` route (used by `modals/EntryContextLocation.svelte` and
`reports/errors/Errors.svelte`). Once the Editor report is gone this 404s. Simplest fix:
remove the "jump to source" hyperlink and show the file:line as plain text in both places
(no replacement editor view is in scope).

**Verification:** `pytest` (backend), frontend unit tests (`npm test` or equivalent in
`frontend/`), then run the app (`fava <ledger>`) and manually confirm: Import/Editor links are
gone from the sidebar, direct navigation to `/<file>/import/` and `/<file>/editor/` no longer
renders those reports, Journal entry-context modal still opens/edits/deletes slices correctly,
BQL query page still has a working editor, Errors report still shows file:line without a dead
link.

---

## Phase 2 — Dashboard report (net worth, allocation, stock/commodity performance)

**Status: ✅ Done**

**Goal:** the core "more intuitive visualization" ask. No new backend data model needed — this
phase is almost entirely wiring existing computations into one new report.

**Backend:**
- Add `get_dashboard()` in `json_api.py` (follow `get_balance_sheet`'s pattern), returning a
  dataclass with: `charts: Sequence[ChartData]` built from `ChartApi.net_worth()` and
  `ChartApi.hierarchy("Assets")` (asset allocation treemap), reusing existing `ChartApi` methods
  as-is.
- Reuse `get_commodities()` unchanged for price history (no backend change needed for
  stock/commodity performance data).

**Frontend:**
- New `frontend/src/reports/dashboard/{index.ts,Dashboard.svelte}` (register via
  `CLIENT_SIDE_REPORTS` + `routes.ts` + `AsideContents.svelte`, same pattern as every existing
  report).
- Net worth + allocation: render the `charts` from `get_dashboard()` via `ChartSwitcher`
  (same as balance sheet) and `Treemap`/`HierarchyContainer` (same as existing hierarchy views).
- Stock/commodity performance: copy the `commodities/index.ts` pattern (`get_commodities()` →
  client-side transform), but normalize each series to % return from its first data point
  instead of raw price, so multiple holdings are comparable on one `LineChart`.
- Make this the sidebar's default/landing report if desired (small change in router default).

**Verification:** run the app against a real ledger, confirm net worth chart matches the
existing Balance Sheet's net worth chart (should be identical data), confirm allocation treemap
matches Balance Sheet's Assets hierarchy, confirm commodity % return lines look sane against
raw prices in the Commodities report for a couple of known holdings.

---

## Phase 3 — Auto-categorization suggester

**Status: ✅ Done**

**Goal:** supplement the existing frecency-based suggestions (`AttributesModule` +
`ExponentialDecayRanker`) for cases they can't handle — a new payee, or a narration variant
that doesn't exactly match history.

**Backend:**
- New `src/fava/core/suggest.py`, a first-party `FavaModule` (not a `fava.ext` extension —
  extensions are for third-party opt-in plugins and add config/indirection this doesn't need,
  and the extension API is a separate candidate for future removal).
- Approach: hand-rolled lightweight text classifier (e.g. bag-of-words/naive-Bayes over
  tokenized payee+narration → account, trained from `ledger.all_entries_by_type.Transaction`
  each `load_file()`, mirroring how `AttributesModule` rebuilds its rankers). No new dependency
  needed at this scale; revisit only if accuracy demands it.
- Wire into `FavaLedger` alongside `attributes` (same lifecycle: rebuilt on file reload).
- New endpoint, e.g. `get_suggest_account(narration: str) -> Sequence[str]`, following the
  `get_payee_accounts` template exactly.

**Frontend:**
- In `frontend/src/entry-forms/suggestions.svelte.ts` (already has the mtime-keyed caching
  layer from the recent commit), call the new endpoint as a fallback when the existing
  payee-based ranker returns nothing, surfaced the same way in `Transaction.svelte`.

**Verification:** unit tests against a synthetic ledger fixture (known payee/narration →
account pairs) checking suggestion quality; manual test in the entry form with a brand-new
payee to confirm a plausible account is suggested where today there'd be none.

---

## Phase 4 — Forecasting / projections

**Status: ✅ Done**

**Goal:** net worth and spending trend projections — plain statistics, not a trained model.

**Backend:**
- New `src/fava/core/forecast.py`, first-party module. Compute linear (or simple seasonal)
  trend fit over the existing `ChartApi.net_worth()`/`interval_totals` series — no new data
  source, just a transform over what Phase 2 already exposes.
- New endpoint(s), e.g. `get_net_worth_forecast()`, `get_category_forecast(account: str)`.

**Frontend:**
- Extend `Dashboard.svelte` with a projected-trend overlay on the net worth chart (e.g. dashed
  continuation line) and a small "at this rate" stat tile per top spending category.

**Verification:** sanity-check projections against a ledger with a known, roughly-linear
trend; confirm the projection line/values move sensibly when filtering by date range.

---

## Phase 5 — Anomaly / insight detection

**Status: ✅ Done**

**Goal:** a "what changed" panel — unusual transactions, new payees, category trend shifts.
Computed on dashboard load (no scheduler infra exists in this codebase; don't add one for v1).

**Backend:**
- New `src/fava/core/insights.py`, first-party module. Per payee/category, flag
  transactions outside a z-score/IQR band of that payee/category's own history; detect
  first-time-seen payees in the current period; compute month-over-month category deltas.
- New endpoint, e.g. `get_insights()`, returning a small list of flagged items for the
  requested date range.

**Frontend:**
- A panel on `Dashboard.svelte` listing flagged items, linking through to the existing Journal
  filtered by account/payee (reuse existing journal filter/link patterns, no new navigation
  primitive needed).

**Verification:** synthetic ledger fixture with one deliberately unusual transaction and one
brand-new payee; confirm both are flagged and nothing else is (check for false positives on
normal recurring transactions).

---

## Overall verification per phase (Phases 1–5)

- Backend: `pytest` in repo root.
- Frontend: existing frontend test suite + `svelte-check`/type-check.
- Manual: run `fava <ledger>` (or the dev server per `frontend/README` if one exists) and click
  through the affected reports in a browser.
- Each phase should land as its own set of commits/PR so Import/Editor removal (highest risk of
  breaking something shared) is isolated from the purely additive dashboard/ML phases.

---
---

# Part 2 — Dark redesign, live stock prices, richer predictions engine

## Context

Phases 1–5 above are done and live on `main`. The user supplied a real design mockup (a
Claude-Artifact-style interactive HTML file, "Dark Beandash design overview") built using this
plan file itself as context, so it's meant to extend — not replace — what's already built. It
shows a dark, IBM-Plex-typeset dashboard with: a net worth hero chart with a forecast line *and*
a confidence band, an allocation grid with drift/cash-runway/unrealized-gains stats, a richer
holdings table with live day-change/P&L/sparklines, a restyled "what changed" insights panel, a
new "Suggester" card that surfaces one transaction needing categorization with one-click-accept
suggested accounts, four forecast tiles (net worth 12M, spend next month, cash flow 90D, FI
target), and a sidebar split into dedicated "Overview" / "Net worth" / "Holdings" / "Predictions"
pages plus the existing ledger reports. The mockup's data is entirely faked (`Math.random()`
jitter on a timer) — it communicates layout, color, typography and interaction, not real logic.

Decisions made with the user for this part:
- Live prices: **Finnhub free tier** (60 req/min). The user will set `FINNHUB_API_KEY` as an
  environment variable themselves — never paste the key value into chat or into files I write.
- **View only** — no new buy/sell transaction-entry UI. Purchases keep going through the existing
  Add Journal Entry form; live prices are a read-only overlay on holdings computed from
  beancount postings as today.
- If Finnhub can't quote a holding (wrong/missing ticker, unsupported exchange, etc.), **fall
  back to the last known beancount-recorded price** for that row rather than erroring or hiding it.
- The "Suggester" card's trigger: a **designated placeholder account** (e.g.
  `Expenses:Uncategorized`), configurable via a new `fava-option`, the same pattern as
  `default-file`/`default-page`. The card surfaces the most recent transaction still posted there.

Research already done (from three parallel Explore passes over the current codebase):
- **Theming is CSS custom properties**, not hardcoded colors. `frontend/css/style.css` defines
  everything (`--background`, `--text-color`, `--border`, `--sidebar-*`, `--button-*`, …) as
  `light-dark(lightVal, darkVal)` pairs; every other stylesheet in `frontend/css/` (`base.css`,
  `charts.css`, `components.css`, `layout.css`, `tree-table.css`, …) consumes only these
  variables. Dark/light is toggled via `frontend/src/stores/color_scheme.ts`
  (`document.documentElement.style.colorScheme`). This means re-theming the whole app is mostly a
  matter of editing the `light-dark()` pairs in `style.css` plus loading IBM Plex Sans/Mono — it
  does **not** require touching most component files.
- **Chart colors are the one exception** — not CSS variables. `frontend/src/charts/helpers.ts`
  builds `colors10`/`colors15` procedurally via a hand-rolled `hclColorRange()` (d3 `hcl()` color
  space) feeding `scaleOrdinal()`-based `currenciesScale`/`treemapScale`/`sunburstScale`/
  `scatterplotScale`. This function's parameters need adjusting to read well on the new dark
  background; it won't follow automatically from the `style.css` change.
- **`suggest.py` already computes real per-account TF-IDF scores** internally
  (`src/fava/core/suggest.py:61-81`) but discards them at the return boundary — it returns
  `sorted(scores, key=scores.__getitem__, reverse=True)`, names only. Exposing `(account, score)`
  pairs is a small, contained change.
- **`forecast.py`'s `forecast()`** (`src/fava/core/forecast.py`) is today a single point-estimate
  linear trend per currency (`TREND_WINDOW=24`, `FORECAST_HORIZON_DAYS=365`), merged directly
  into the "Net Worth" `BalancesChart`'s `data` array in `get_dashboard()`
  (`src/fava/json_api.py`), distinguished from history only by a `" (projected)"` currency-key
  suffix. No confidence band, no r², no other forecast type exists yet — but `g.ledger.charts.
  interval_totals(...)` (already used for Income Statement) gives the same `DateAndBalance`-
  shaped series for Expenses/Income, so the identical `forecast()`/`_linear_fit()` machinery
  applies directly to a spend or cash-flow forecast with no new data plumbing.
- **`insights.py`** is payee-level only (`new_payee`, `unusual_transaction` via leave-one-out
  z-score) — no category-trend insight exists; out of scope to add for this part unless it comes
  up again.
- **Holdings today is a raw BQL report**, no dedicated backend endpoint —
  `frontend/src/reports/holdings/index.ts` runs hand-written BQL query strings (`all`,
  `by_account`, `by_currency`, `by_cost_currency`) through the generic `get_query()` API, and
  `getprice()` inside BQL resolves to *whatever the latest recorded `price` directive is*, not a
  live quote. **There is zero existing live/external-fetch infrastructure anywhere in this
  codebase** (confirmed: no `beanprice` dependency, no scheduler/APScheduler/timer of any kind —
  the only background thread is `watcher.py`'s local-filesystem watch). A live-price feature
  needs a new, isolated piece: a backend endpoint the frontend polls on an interval, whose result
  is merged client-side on top of the existing cost-basis/BQL data — not a new scheduled job.
- `g` request context (`src/fava/_ctx_globals_class.py`) already exposes `g.filtered`, `g.conv`,
  `g.interval`, `g.ledger` — every new endpoint below reuses these exactly like `get_dashboard`
  does, no new plumbing.
- Test patterns to follow: `tests/test_core_forecast.py` / `test_core_insights.py` /
  `test_core_suggest.py` use a `_FakeLedger`/`SimpleNamespace(Transaction=[...])` fixture
  (building transactions via `fava.beans.create.transaction(...)`) to unit-test a module in
  isolation; `tests/test_json_api.py` uses the real `test_client` fixture against the
  `long-example` ledger with snapshot tests for full endpoint responses.

Reference palette from the mockup (`Beandash.dc.html`, kept for implementation — not to be
pixel-matched in light mode, just used as the dark-mode target and a loose analog for light):
background `#0a0b0d`, card `#101317`, border `#1c2027`, text `#e8eaed`, muted text `#6b7280`/
`#8b929c`, accent green `#5fd6a0` (actual/positive), purple `#9d8cf5` (forecast), amber `#f0b45f`
(warning/drift), red `#f0705f` (negative). Fonts: IBM Plex Sans (UI), IBM Plex Mono (all numeric/
tabular values, tickers, labels) via Google Fonts.

---

## Phase 6 — Dark theme & typography (global)

**Status: ✅ Done**

**Goal:** land the new visual language app-wide before building new pages on top of it, so every
existing report (Journal, Balance Sheet, Query, old Holdings, etc.) picks it up for free.

- `frontend/css/style.css`: update the dark side of each `light-dark()` custom-property pair to
  the new palette; keep light mode's *structure* (still uses the same variables) but give it a
  reasonable analog of the new accent hues rather than a pixel-matched second design (none was
  provided for light mode).
- Load IBM Plex Sans/Mono (self-host or Google Fonts `<link>`, matching the mockup's `helmet`
  block) via `frontend/css/fonts.css` or the base HTML template, and set them as the default
  font-family alongside the existing font stack fallbacks. Use the mono face for numeric/tabular
  values app-wide (existing tables already have some monospace usage to check/extend).
- `frontend/src/charts/helpers.ts`: adjust `hclColorRange()`'s chroma/luminance/hue parameters so
  the generated categorical palette (currency lines, treemap, sunburst) reads well against the
  new dark background; sanity-check against light mode too since it's the same function.
- Card/border-radius/spacing conventions (16px card radius, 10px chip radius, `#1c2027` borders)
  belong in `components.css`/`layout.css` as shared classes so new Phase 7–10 components can use
  them instead of one-off inline styles.

**Verification:** run the app, visually check Journal/Balance Sheet/Query/Holdings/Options still
render correctly (no broken contrast/invisible text) in both light and dark, `svelte-check`/
`eslint`/`biome check` clean, existing frontend test suite still green (pure CSS change, no
logic).

---

## Phase 7 — Predictions engine backend upgrades

**Status: ✅ Done**

**Goal:** all the new statistical outputs the design needs, as small additions to the existing,
already-tested `forecast.py`/`suggest.py`/`insights.py` modules and `json_api.py` endpoints —
no new dependency, same hand-rolled-stats philosophy as Phase 4.

- **Confidence band + r² on the net worth forecast**: extend `forecast()` (or add a sibling
  function) in `core/forecast.py` to also return, per currency, a residual-based prediction
  interval that widens with distance from `TREND_WINDOW`'s fit (e.g. `± k * residual_stdev *
  sqrt(i)`), plus the fit's r² (`1 - ss_res/ss_tot`, same formula the mockup's demo JS uses).
  Wire into `get_dashboard()`'s `BalancesChart` as two more suffixed series (e.g.
  `"USD (projected high)"`/`"USD (projected low)"`) so the existing `LineChart`/`ParsedLineChart`
  machinery renders them with no frontend chart-code changes — same trick already used for the
  point-estimate forecast line.
- **Spend forecast / cash-flow forecast**: new functions/endpoints reusing
  `g.ledger.charts.interval_totals(g.filtered, g.interval, options["name_expenses"], g.conv)`
  (Expenses) and the income equivalent, fed through the same linear-fit machinery as net worth,
  to project next month's spend and 90-day cash flow (income − expenses).
- **FI target**: a small calculator — years until the net-worth trend crosses `25 × trailing
  annual spend` (the "4% rule"), derived from the existing net worth trend slope and the spend
  forecast above. No new data source.
- **`suggest.py` confidence scores**: change `SuggestModule.suggest_accounts()` to return
  `Sequence[tuple[str, float]]` (raw TF-IDF-style score, not yet a bounded confidence), update
  `get_suggest_accounts` in `json_api.py` and the frontend validator/type accordingly; normalize
  to a 0–100% bar client-side (e.g. relative to the top score) rather than pretending it's a
  calibrated probability server-side.
- **Uncategorized-transaction detection**: new `fava_options.py` option (e.g.
  `uncategorized_account`, default `"Expenses:Uncategorized"`, same `parse_option_custom_entry`
  pattern as `default_page`); new endpoint that finds the most recent transaction with a posting
  to that account and returns it plus `suggest_accounts()`'s top matches for it.
- New/updated dataclasses and `@api_endpoint`s in `json_api.py` for all of the above, following
  the existing `get_dashboard`/`get_insights` template exactly.

**Verification:** unit tests per module (`_FakeLedger` pattern) covering the confidence-band
math on a synthetic linear series (known slope → known band width), the spend/cash-flow
forecasts, the FI-target calculator's edge cases (already above target, no expense history), and
the uncategorized-transaction lookup; `test_json_api.py` snapshot/assertion tests for each new
endpoint; keep the 100%-coverage bar (`pytest --cov=fava --cov-fail-under=100`) the rest of this
codebase holds.

---

## Phase 8 — Overview page rebuild (frontend)

**Status: ✅ Done**

**Goal:** rebuild `frontend/src/reports/dashboard/{index.ts,Dashboard.svelte}` to match the
mockup's Overview layout, on top of the Phase 6 visual system and Phase 7 data.

- Net worth hero card: current value + 30-day delta, projected-12M + r² stat, savings-rate stat,
  the net worth chart with actual/forecast/band (reusing `LineChart`'s existing multi-series
  rendering — the band renders as a filled area between the two new suffixed series, similar to
  how `LineChart.svelte`'s existing area-mode fill works, extended if needed for a band-between-
  two-lines fill rather than area-to-zero).
- Allocation panel: rebuild as the grid-of-tiles layout (reusing the existing
  `ChartApi.hierarchy()` data already fetched for the Assets treemap, just a different
  presentation component instead of `Treemap.svelte`), plus the three new stat rows (equities
  drift vs. target, cash runway, unrealized gains) — cash runway and unrealized gains are
  derivable from existing balance-sheet/holdings data; "drift vs. target" needs a user-settable
  target allocation, which can be a new simple `fava_options` entry (e.g. free-text per top-level
  asset category) or deferred/hidden if no target is configured.
- Holdings preview table and "What changed" insights panel: restyle to match (monospace numeric
  columns, colored P/L, tone-colored left border on insight cards); insights panel already has
  the right data shape (`type`/`payee`/`message`/`entry_hash`) from Phase 5, just needs the new
  visual treatment — the mockup's separate "title"/"detail" text can both come from `message`
  (or split `message` into two fields later if it's worth it once this is in front of real data).
- New "Suggester" card component: fetch the Phase 7 uncategorized-transaction endpoint, render
  the transaction plus ranked suggested accounts with confidence bars (reusing
  `AccountInput.svelte`/the `suggestions.svelte.ts` fetch-cache pattern where sensible), "Accept
  top match" writes the account onto that transaction's placeholder posting (reuse the existing
  entry-editing API, e.g. `put_source_slice`/`save_entry_slice` plumbing already used by the
  Journal context modal) and "Edit" jumps to it via the same `#context-<hash>` link pattern
  already used by Insights (Phase 5).
- Forecast tiles row: four tiles driven by the Phase 7 endpoints.

**Verification:** run the app against a real ledger, visually compare each panel to the mockup;
confirm "Accept top match" actually updates the transaction's account in the beancount file and
the card advances/clears; `svelte-check`/`eslint`/build clean; extend frontend unit tests if any
new pure logic (e.g. band-fill path construction) is added.

---

## Phase 9 — Live stock prices (Finnhub)

**Status: ✅ Done**

**Goal:** a read-only live-price overlay, isolated from the core ledger-derived data model.

- New `src/fava/util/live_prices.py` (or `core/live_prices.py` if it needs ledger context): a
  `fetch_quotes(symbols: Sequence[str]) -> dict[str, Quote]` using stdlib `urllib.request` (no
  new dependency) against Finnhub's `GET /api/v1/quote?symbol=X&token=<key>`. Reads the API key
  from `os.environ["FINNHUB_API_KEY"]` only — never written to a file or accepted as a request
  parameter. Short in-memory TTL cache (e.g. 15s) to dedupe rapid repeated calls (multiple tabs/
  fast polling) and stay well inside Finnhub's 60 req/min free-tier limit for a handful of
  holdings polled every 30–60s.
- New endpoint, e.g. `get_live_prices(tickers: str)` (comma-separated, following the existing
  string-param convention) in `json_api.py`, returning per-ticker `{price, day_change_pct,
  as_of}` for symbols Finnhub can quote; tickers not found are simply omitted from the response
  (per the "fall back to last known beancount price" decision, the frontend keeps the existing
  BQL-derived price for any ticker missing from this response — no error state needed for that
  case specifically). Assumes beancount commodity/currency code == ticker symbol (the standard
  convention already used in this ledger); note as a known limitation, not solved generically.
  If `FINNHUB_API_KEY` isn't set, the endpoint returns an empty result set (live prices simply
  don't appear anywhere) rather than erroring — this stays fully optional infrastructure.
- Frontend: new richer Holdings table (used by both the Overview preview and the new dedicated
  Holdings page, Phase 10) — cost basis/units from the existing BQL data, live price/day-change/
  P&L layered on top via a `setInterval` poll of the new endpoint (mockup polls ~1.4s but that's
  demo-jitter theater; real quotes don't move that fast on a free tier — poll every 30–60s), a
  "Live marks on/off" toggle (per-session UI state, mirrors the mockup's toggle) that pauses the
  polling, sparkline per holding built from the existing historical `get_commodities()` series
  (not from live polling, which has no history yet).

**Verification:** unit test `fetch_quotes`/the cache against a mocked HTTP layer (no real network
calls in tests); `test_json_api.py` test for the endpoint with `FINNHUB_API_KEY` unset (empty
result, no error) and with a monkeypatched fetch function; manual check with a real key set that
quotes appear and update on poll, and that toggling "Live" off stops requests (check Network
tab).

---

## Phase 10 — Dedicated Net worth / Holdings / Predictions pages + sidebar restructure

**Status: ✅ Done**

**Goal:** match the mockup's sidebar IA — a "DASHBOARDS" group (Overview, Net worth, Holdings,
Predictions) above a "LEDGER" group (Journal, Balance sheet, Income statement, Trial balance,
Query console) — without breaking the existing Holdings BQL report's URL/route users may already
rely on.

- `frontend/src/sidebar/AsideContents.svelte`: restructure into the two labeled groups matching
  the mockup (small style addition to render a group header, reusing the "DASHBOARDS"/"LEDGER"
  label styling from Phase 6's shared classes).
- "Net worth" page: new route, effectively the Overview's net worth hero card promoted to a
  full-page deep-dive (larger chart, longer history, maybe the allocation panel alongside it) —
  mostly composition of components already built in Phase 8, not new logic.
- "Holdings" page: new route hosting the Phase 9 richer live-price table full-page. Decide
  whether this **replaces** the sidebar link to the old BQL-based `/holdings/` report (keeping
  the old route itself alive and reachable by direct URL/bookmark, just unlinked) or keeps both
  linked under different names — default to replacing the link but leaving the old route
  functional, flag this for the user to confirm once they see it rather than guessing further.
- "Predictions" page: new route hosting the four forecast tiles (Phase 7/8) plus the net worth
  forecast chart, full-page.
- Register each via the existing pattern (new `frontend/src/reports/<name>/{index.ts,*.svelte}`,
  add to `frontend_routes` in `routes.ts`, add to `CLIENT_SIDE_REPORTS` in `application.py`,
  add a `<Link>` in `AsideContents.svelte`) — identical mechanics to how `dashboard` was added
  in Phase 2.

**Verification:** navigate to each new sidebar link, confirm it renders the right content and
the old `/holdings/` route (if kept unlinked) still works by direct URL; `pytest`
(`test_application.py`-style report-registration coverage) and full frontend check suite.

---

## Overall verification for Part 2

Same bar as Phases 1–5: `pytest --cov=fava --cov-fail-under=100`, `ruff check`/`format`, `mypy`,
`ty check`, `svelte-check`, `eslint`, `biome check`, frontend unit test suite, and a manual
in-browser pass per phase (screenshots/DOM checks against the mockup where useful). Land each
phase as its own commit (matching the granularity used for Phases 1–5) so a regression is easy
to bisect to one phase.
