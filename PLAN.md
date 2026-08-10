# Beandash: fava fork — phased feature plan

## Status

Phases 1–10 (Part 1 + Part 2) done and pushed to `main`. Part 3 (below) is a new round matching
the app precisely to the design mockup and is not yet started.

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
| 11 — Remove reports not in the design | ✅ Done |
| 12 — Sidebar chrome (logo, status dots, footer) | ⏳ Pending |
| 13 — Overview header (greeting, time pills) | ⏳ Pending |
| 14 — Bespoke net worth chart | ⏳ Pending |
| 15 — Allocation tile grid | ⏳ Pending |
| 16 — Holdings table redesign | ⏳ Pending |
| 17 — Insights redesign | ⏳ Pending |
| 18 — Suggester redesign | ⏳ Pending |
| 19 — Forecast tiles redesign | ⏳ Pending |
| 20 — Shared visual language on ledger reports | ⏳ Pending |

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

**Status: 🔄 In progress**

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

**Status: ⏳ Pending**

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

**Status: ⏳ Pending**

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

---
---

# Part 3 — Match the app precisely to the design mockup

## Context

Parts 1 and 2 got the app functionally where it needed to be (dashboard, forecasting, suggester,
insights, live prices, dedicated pages) but the visual/interaction fidelity to the supplied
mockup (`Beandash.dc.html`, re-extracted from `Dark Beandash design overview.zip` for this part)
was approximate — built from the mockup's general "feel" rather than its exact spec. The user has
now asked to match the mockup precisely, add whatever features it depicts that aren't built yet,
remove sidebar tabs that aren't in the mockup, and extend the same visual language to the reports
the mockup didn't cover (Journal, Balance Sheet, Income Statement, Trial Balance, Query).

Decisions confirmed with the user for this part:
- **Reports not in the mockup (Documents, Events, Statistics, and the standalone Commodities
  report page) are removed entirely** — backend and frontend, not just unlinked. (The
  `get_commodities` *API endpoint* survives regardless — see Phase 11 — because the Overview's
  performance chart and Holdings' sparklines call it directly as a data source, not as a report.)
- **Options, Help, and Errors stay in the sidebar** even though the mockup's sidebar doesn't show
  a utility section — they're basic app admin, not "content" tabs the mockup was depicting.
- **The net worth chart becomes a bespoke SVG component** matching the mockup exactly (actual
  line + dashed forecast + confidence band + "today" marker, no controls), replacing Fava's
  generic interactive `ChartSwitcher` for that one spot. This trades away that chart's
  multi-currency toggle/zoom/area-switch/interval-picker controls in exchange for pixel-level
  fidelity to the mockup.
- **The other reports (Journal/Balance Sheet/Income Statement/Trial Balance/Query) get the shared
  visual language** (card/label/mono-number/color vocabulary), not a from-scratch redesign —
  there's no mockup spec for them to match precisely.

Research already done (full removal-footprint trace via a dedicated Explore pass, plus direct
reads of `internal_api.py`, `core/insights.py`, `core/fava_options.py`, `core/tree.py` for this
part) — the key facts every phase below relies on:
- The mockup's full HTML/CSS/seed-data is at
  `/tmp/claude-1000/-home-kevin-Projects-beandash/10663caa-69ab-43c3-a899-a48f8e662ac3/scratchpad/design_review/Beandash.dc.html`
  (re-extract from the zip if that scratchpad is gone by the time this phase starts — the zip
  itself, `Dark Beandash design overview.zip`, stays in the repo root, untracked, private).
  Colors/copy/geometry below are taken directly from it.
- `get_commodities()` (`json_api.py`) and its `CommodityPairWithPrices` dataclass, the frontend
  `get_commodities` API wrapper, `commodities_validator`/`Commodities` type, and the `commodities`
  entry in `frontend/src/reports/routes.ts`'s import list **must all survive** Phase 11 — only the
  *report page* (`frontend/src/reports/commodities/*`, its nav link, its `CLIENT_SIDE_REPORTS`
  entry) goes. Same "endpoint survives, page goes" split applies to nothing else — Documents,
  Events, and Statistics genuinely lose their backend endpoints too (see Phase 11's per-report
  breakdown for exactly what's shared vs. removable in each).
- `core/documents.py` (whole module), the `Document`/`Event` entry classes in
  `frontend/src/entries/index.ts`, the `DocumentUpload.svelte` modal and its droptargets (in
  `AccountReport.svelte`, `JournalTable.svelte`, `AccountPageTitle.svelte`, `AccountCell.svelte`),
  and the `ScatterPlot` chart type (part of the generic `charts_validator` tagged union used by
  the extension-chart mechanism, independently unit-tested) are all **shared infrastructure that
  must not be touched** even though Documents/Events are going away as reports.
- `LedgerData` (`internal_api.py:53`) has no total-entry-count field today; `ledger.all_entries`
  (`core/__init__.py:327`) is directly available to add one for the new sidebar footer.
- `TreeNode.serialise()` (`core/tree.py:61`) already returns per-child `balance_children`
  (a `SimpleCounterInventory`, i.e. `dict[str, Decimal]`) at market value when called with
  `AT_VALUE` — the same mechanism `get_dashboard()`'s `unrealized_gain` already uses. This is
  reused directly for the new Allocation tile-grid endpoint in Phase 15, no new tree-flattening
  logic needed.
- `Insight` (`core/insights.py:80`) is currently `{type, payee, message, entry_hash}` — Phase 17
  splits `message` into `title`/`detail`/`value`/`tone`, reusing the exact same z-score/new-payee
  detection logic in `insights()`, just changing what gets constructed at the two `found.append(...)`
  call sites.

---

## Phase 11 — Remove reports not in the design

**Status: ✅ Done**

**Goal:** delete Documents, Events, Statistics, and the standalone Commodities report page
(backend + frontend), while keeping every piece of shared infrastructure they sit on top of
intact. This is the same kind of surgical removal as Phase 1 (Import/Editor) — most of the risk
is in *not* deleting something load-bearing, not in the deletion itself.

**Commodities** (endpoint survives, page goes):
- Delete `frontend/src/reports/commodities/` (`Commodities.svelte`, `CommodityTable.svelte`,
  `index.ts`).
- Remove `"commodities"` from `CLIENT_SIDE_REPORTS` (`application.py`), from `frontend_routes`
  (`routes.ts`), and its `<Link>` in `AsideContents.svelte`.
- Keep: `get_commodities()`/`CommodityPairWithPrices` in `json_api.py`, the frontend
  `get_commodities` wrapper, `commodities_validator`/`Commodities` type — all still called
  directly by `net_worth_data.ts` and `HoldingsPreview.svelte`.

**Documents** (the riskiest — most shared infrastructure):
- Delete: `frontend/src/reports/documents/` (all 6 files), `frontend/src/editor/
  DocumentPreviewEditor.svelte`, `frontend/test/reports.test.ts`.
- Delete backend: `get_documents()` and `put_move()` (+ its `NotAFileError`) in `json_api.py`;
  remove `get_documents`/`move_document` and the `"documents"`/`"move"` entries from
  `frontend/src/api/index.ts`.
- Remove `"documents"` from `CLIENT_SIDE_REPORTS`/`routes.ts`/`AsideContents.svelte`.
- **Keep untouched:** `core/documents.py` (whole module — still used by `put_add_document`,
  `delete_document`, and the `document`/`statement` Flask routes), `put_add_document`,
  `put_attach_document`, `delete_document` in `json_api.py`, the `Document` entry class,
  `DocumentUpload.svelte` and all four of its droptargets, `_journal_table.html`'s Document-entry
  rendering, `tests/test_core_documents.py` (tests the shared module, not the report).
- Edit `tests/test_json_api.py::test_api_add_document_and_move_and_delete` to drop only the
  move-specific assertions (~lines 156-179), keeping the add/document-GET/delete assertions.
- Delete `tests/__snapshots__/test_json_api-test_api-documents.json`; remove the `("documents",
  ...)` case from `test_api`'s parametrize list in `test_json_api.py`.

**Events:**
- Delete `frontend/src/reports/events/` (all 3 files).
- Delete `get_events()` in `json_api.py`; remove `get_events` and `"events"` from
  `frontend/src/api/index.ts`.
- Remove `"events"` from `CLIENT_SIDE_REPORTS`/`routes.ts`/`AsideContents.svelte`.
- **Keep:** the `Event` entry class, `core/misc.py::upcoming_events()`, the `ScatterPlot` chart
  type/component (used generically by the extension-chart mechanism, has its own test).
- **Also remove** (orphaned once the Events nav badge is gone — confirmed zero other consumers):
  `upcoming_events_count` from `LedgerData` (`internal_api.py`) and `ledgerDataValidator`
  (`validators.ts`), the `upcoming_events: int = 7` fava-option (`core/fava_options.py:112`) and
  its doc section in `help/options.md`. `core/misc.py::upcoming_events()` itself and
  `FavaMisc.upcoming_events` stay (harmless, cheap, and removing them would touch more than this
  cleanup is worth) — just nothing computes/exposes the *count* anymore.
- Delete `tests/__snapshots__/test_json_api-test_api-events.json`; remove the `("events", ...)`
  case from `test_api`'s parametrize list.
- Edit `frontend/test/end-to-end-validation.test.ts`'s `"validate events"` test to pull an Event
  entry out of the (still-present) `test_json_api-test_api-journal.json` snapshot instead of the
  deleted `events.json`, so `Event.validator` parsing stays exercised.

**Statistics:**
- Delete `frontend/src/reports/statistics/` (all 4 files).
- Delete `get_statistics()`/`Statistics` dataclass in `json_api.py`; remove `get_statistics` and
  `"statistics"` from `frontend/src/api/index.ts`; delete `statistics_validator` from
  `validators.ts`.
- Remove `"statistics"` from `CLIENT_SIDE_REPORTS`/`routes.ts`/`AsideContents.svelte`.
- **Keep:** `AccountIndicator.svelte`, `account_details` store, `core/accounts.py::balance_string`/
  `uptodate_status` (power the generic up-to-date indicators, used elsewhere), `QueryTable.svelte`.
- Also remove `core/accounts.py::AccountDict.all_balance_directives()` (its only caller was
  `get_statistics()`) and trim its one assertion out of the `tests/test_core.py` test that
  otherwise covers `balance_string` (don't delete that whole test).
- Delete `tests/__snapshots__/test_json_api-test_api-statistics.json`; remove the `("statistics",
  ...)` case from `test_api`'s parametrize list.

**Cross-cutting cleanup:**
- `tests/test_application.py::test_client_side_reports` currently uses `/documents/` as an
  arbitrary "does the client-side shell render" baseline — repoint it at a surviving report (e.g.
  `/commodities/` or `/journal/`) instead of deleting the test.
- Sanity-check `frontend/src/keyboard-shortcuts.ts` / any help docs (`help/features.md`,
  `help/*.md`) for now-dead mentions of the removed reports' shortcuts (`g d`, `g E`, `g s`) or
  screenshots/links.

**Not in scope for this phase:** the old BQL-based `/holdings/` report (unlinked from nav back in
Phase 10, still reachable by direct URL) — the user wasn't asked about this one specifically, so
it's left as-is; flag to the user once this phase is visible in case they want it fully removed
too as a follow-up.

**Verification:** `pytest --cov=fava --cov-fail-under=100`, `ruff`/`mypy`/`ty` clean, `svelte-
check`/`eslint`/`biome`/build clean, frontend test suite green, then a manual pass confirming:
sidebar no longer shows Documents/Events/Statistics/Commodities, direct navigation to their old
URLs 404s, but Journal still renders Document/Event entries inline, attaching a document to a
transaction from the entry editor still works, Overview's performance data and Holdings'
sparklines still load (proving `get_commodities` survived).

---

## Phase 12 — Sidebar chrome (logo, status dots, footer)

**Goal:** the sidebar's non-navigation chrome from the mockup — brand mark, per-item status dots,
and the bottom filename/live/entry-count block.

- **Logo + wordmark**: small addition at the top of `AsideContents.svelte` (or a new
  `SidebarHeader.svelte` if `AsideContents.svelte` is getting crowded) — a 26px rounded square
  with a green gradient (`linear-gradient(150deg, #5fd6a0, #2c9c78)`) containing a "b" in
  `IBM Plex Mono` 600 weight, plus "Beandash" in the body font at 600 weight. Static, no data
  needed.
- **Per-item status dot**: each `DASHBOARDS` link gets a small 6px dot before its label — accent
  green (`--green`) when that link is the active/selected report, dim gray (`#2c3138`)
  otherwise. `SidebarLink.svelte` already computes `selected` via `href.includes($pathname)`
  (`route.ts:26`) — thread that through as a prop (or add a small dot slot) rather than
  recomputing selection state elsewhere.
- **Sidebar footer**: new block below the existing nav groups showing: the ledger filename
  (basename of `$ledgerData.options.filename`), a small pulsing dot + label reflecting whether
  the file-watcher/auto-reload is active (reuse the existing `changed`-polling mechanism in
  `app.ts`'s `pollForChanges` / the `mtime` store — a live dot when polling is actively running,
  not a fake "market open" concept), and "`N entries · M errors`" using `$errors.length` (already
  available) and a new `entries_count: int` field added to `LedgerData`
  (`internal_api.py`, trivially `len(ledger.all_entries)`) threaded through
  `ledgerDataValidator`.
- Add the small `.nav-group-label`-adjacent structural CSS for this (badge/dot classes) to
  `components.css` alongside the existing `.card`/`.card-label` vocabulary from Phase 6, so it's
  available to other phases too.

**Verification:** visual check in both dark and light mode (mockup is dark-only — pick a
reasonable light-mode analog for the dot colors, don't leave light mode broken), confirm the
active-page dot moves correctly when navigating between Overview/Net worth/Holdings/Predictions,
confirm entry/error counts match what Journal/Errors report independently, `pytest`/`svelte-
check`/`eslint`/build clean.

---

## Phase 13 — Overview header (greeting, time-range pills)

**Goal:** translate the mockup's page header — which is mockup-only content sitting *inside* the
main content area, not Fava's actual global `<header>` bar (which holds the real time/account/tag
filter inputs used by every report and must stay reachable everywhere) — into real content at the
top of the Overview report specifically.

- New small header block at the top of `Dashboard.svelte` (or its own `OverviewHeader.svelte`):
  an eyebrow line ("OVERVIEW · {date}", `IBM Plex Mono`, `--text-color-lightest`) and a greeting
  headline sized off local time-of-day ("Good morning"/afternoon/evening) plus a simple
  reconciliation status derived from `$errors.length` (0 errors → "Everything reconciled.", N
  errors → "N error(s) to review." linking to the Errors report). Static/derived, no new backend
  needed.
- **Time-range pills (1M/6M/YTD/2Y/ALL)**: implemented as a convenience row that *writes into
  Fava's existing `time` URL filter* rather than a second competing filter system — each pill
  sets `time` to an equivalent preset (`1M`→last full month, `6M`→a 6-month-back date range,
  `YTD`→current year, `2Y`→2-year-back range, `ALL`→clear the param) via the same
  `stores/filters.ts`/URL-param mechanism the existing Time combobox already uses. Highlight
  whichever pill matches the current `time` param, if any (none highlighted if it's a custom
  value the pills don't cover — that's expected, the real Time filter box is still there for
  anything more specific).
- **Live toggle**: stays scoped to the Holdings card (where it already lives, controlling the
  actual Finnhub poll) rather than being promoted to a page-wide header control — net worth
  itself isn't live-quoted, so a page-level "live" toggle would be decorative/misleading. This is
  a deliberate simplification from the mockup; flag it to the user once visible in case they'd
  rather it be page-wide for visual consistency even if it only functionally affects Holdings.

**Verification:** confirm greeting text changes with system time (spot-check by temporarily
mocking the clock or just eyeballing at different times of day), confirm each pill actually
changes the underlying `time` filter (check the URL updates and other filtered data reacts),
confirm error count in the header matches the Errors report, `svelte-check`/`eslint`/build clean.

---

## Phase 14 — Bespoke net worth chart

**Goal:** a small new SVG component matching the mockup's net worth chart exactly, replacing
`ChartSwitcher` in `NetWorthHero.svelte` (both the Overview card and the full `/net_worth/` page
use this).

- New `frontend/src/reports/dashboard/NetWorthChart.svelte`. Props: the actual history series and
  forecast/band series for the ledger's operating currency — reshape these client-side from the
  already-fetched `charts[0]` (`ParsedLineChart`, currency-keyed `" (projected)"`/`" (projected
  high)"`/`" (projected low)"`-suffixed data, same suffixes `forecast.py`/`get_dashboard()`
  already produce) inside `net_worth_data.ts`, rather than adding a new backend endpoint — the
  data's already there, this is purely a client-side reshape into the flat number arrays an SVG
  path-builder needs.
- Render, per the mockup's exact geometry (`viewBox="0 0 900 240"`): 3 horizontal gridlines (no
  axis labels on them), a solid green actual line with a soft translucent area fill under it, a
  dashed purple forecast line continuing from the last actual point, a translucent purple
  confidence band (upper/lower forecast bounds, filled polygon), a dashed vertical "today" marker
  at the actual/forecast split, x-axis labels at start/mid/today/end, and the 3-item legend row
  (actual / forecast / 80% band swatches) below the chart — colors/strokes lifted directly from
  the mockup's inline SVG (`#5fd6a0` actual, `#9d8cf5` forecast/band, `rgba(...)` fills).
- `NetWorthHero.svelte` swaps `<ChartSwitcher {charts} />` for `<NetWorthChart ... />`. Since this
  drops the Assets-treemap and Performance chart tabs from the Overview/Net-worth pages: the
  Assets allocation view is superseded by the new tile-grid card (Phase 15) and the Performance
  (commodity % return) tab has no mockup equivalent and is dropped from Overview — its data
  source (`get_commodities`) keeps being used for Holdings' sparklines, so nothing backend-side is
  wasted. `performance_chart()`/the `Commodities` fetch in `net_worth_data.ts` can be deleted
  once nothing calls it (double check `HoldingsPreview`'s own `get_commodities` call is
  independent, not reused from this function, before deleting).

**Verification:** confirm the chart renders sensibly against `long-example.beancount` (visually
compare band width growing with forecast distance, "today" marker lines up with the actual/
forecast split), confirm both Overview and the full Net worth page render it correctly, add a
frontend unit test for the reshape function (`net_worth_data.ts`) similar in spirit to existing
chart-helper tests, `svelte-check`/`eslint`/build clean.

---

## Phase 15 — Allocation tile grid

**Goal:** replace the Assets-treemap tab (now gone per Phase 14) with the mockup's grid-of-tiles
allocation card, plus its "cash runway" and "unrealized gains" stat rows. ("Equities drift vs.
target" needs a user-defined target allocation that doesn't exist yet — see below.)

- New backend endpoint `get_allocation()` in `json_api.py`: `g.filtered.root_tree.get(options
  ["name_assets"]).serialise(AT_VALUE, g.ledger.prices, g.filtered.end_date).children`, one row
  per direct child of the Assets root — reuses exactly the mechanism `get_dashboard()`'s
  `unrealized_gain` already uses (`core/tree.py::TreeNode.serialise`), no new tree logic. Returns
  `{account, balance, pct_of_total}[]` in the operating currency, sorted descending by balance.
- New `AllocationGrid.svelte`: CSS grid of tiles sized/colored by percentage (reuse the existing
  `hclColorRange`-derived palette from `charts/helpers.ts`, already tuned for the dark theme in
  Phase 6, rather than hand-picking mockup-specific hex colors per category — the mockup's fixed
  category list (US equities/Intl equity/etc.) is example seed data, not something to hardcode
  since real ledgers have arbitrary account names).
- **Cash runway** stat: liquid cash ÷ trailing monthly spend. Liquid cash = sum of `get_holdings()`
  rows where `cost_currency` is `None` and `currency` matches the operating currency (already the
  exact shape of "plain cash held directly" rows, confirmed in Phase 9's manual testing). Trailing
  monthly spend = expose `trailing_annual_spend / 12` from `get_predictions()`'s existing internal
  computation (currently computed but not returned — add a field rather than recomputing).
- **Unrealized gains** stat: already computed as `get_dashboard()`'s `unrealized_gain` — just
  render it in this card instead of (or in addition to) the hero's existing stat.
- **Equities drift vs. target**: genuinely blocked on a target-allocation config that doesn't
  exist. Default: show the row with a muted "—" / "not configured" state (matching the mockup's
  row *position* without fabricating a number) rather than skip it entirely or block the phase on
  designing a new fava-option. If the user wants it live now, that's a separate, explicit follow-
  up (needs deciding what counts as "equities" and how the user specifies a target %).

**Verification:** tile grid renders sensibly for `long-example.beancount`'s account structure,
percentages sum to ~100%, cash runway/unrealized gains numbers are sane, `pytest --cov=fava
--cov-fail-under=100` for the new endpoint, `svelte-check`/`eslint`/build clean.

---

## Phase 16 — Holdings table redesign

**Goal:** restyle `HoldingsPreview.svelte` (used by both the Overview preview and the full
`/holdings_live/` page) to the mockup's exact column set and chrome.

- Columns become: **TICKER** (ticker only — the mockup's name subtitle needs a friendly
  commodity display name; check `ledger.commodities.names`/`currency_names` — already exposed on
  `LedgerData` — for a usable name, else drop the subtitle rather than fabricate one), **UNITS ·
  BASIS** (stacked: units, then "@ avg cost" below), **LAST** (price, colored white while live
  data is present for that ticker and the dimmer default text color otherwise), **DAY** (existing
  day-change %), **P/L** (new: `market_value - book_value` as a dollar figure, with the existing
  `unrealized_profit_pct` below it — replaces the separate Market Value/Unrealized columns),
  **30D** (existing sparkline, repositioned to match).
- Header row subtitle ("cost basis from beancount lots · marks streaming") and a right-aligned
  status indicator — simplify the mockup's fake NYSE-hours awareness to reflect our own actual
  polling state ("Live · updated Ns ago" / "Live marks off") rather than inventing market-hours
  logic requiring timezone/holiday handling.
- Footer row: "N positions · N accounts" (add `account_count` to `get_holdings()`'s query via
  `count(distinct(account))` grouped alongside the existing columns — verify beanquery's exact
  `distinct()` syntax during implementation; fall back to counting positions/lots if accounts
  aren't cleanly countable that way) and "market value {total}" (already computable client-side
  by summing the existing rows).
- "Live marks on/off" toggle restyled to the mockup's pill chip look; behavior unchanged from
  Phase 9.

**Verification:** table renders correctly for holdings with and without live quotes, with and
without a commodity display name, footer counts match the actual data, `pytest --cov=fava
--cov-fail-under=100` for the `account_count` query change, `svelte-check`/`eslint`/build clean,
manual check that toggling live still pauses/resumes polling correctly (regression check against
Phase 9's behavior).

---

## Phase 17 — Insights ("What changed") redesign

**Goal:** match the mockup's insight-card layout — colored left bar, title, detail line, and a
right-aligned colored value badge — which needs `Insight` split into structured fields instead of
one pre-formatted `message` string.

- `core/insights.py`: change `Insight` from `{type, payee, message, entry_hash}` to `{type,
  payee, title, detail, value, tone, entry_hash}`. Update the two `found.append(Insight(...))`
  call sites (`insights()`, lines ~149 and ~172) to construct the new fields directly instead of
  formatting one string — this is the same underlying z-score/new-payee logic, just building
  structured output:
  - `new_payee`: `title=f"New payee: {payee}"`, `detail=f"First seen {entry.date}"`,
    `value="new"`, `tone="amber"`.
  - `unusual_transaction`: `title=f"Unusual amount for {payee}"`,
    `detail=f"{amount:.2f} vs. usual {mean:.2f}"`, `value=f"{pct:+.0f}%"` (signed % vs. the
    leave-one-out mean, guard `mean == 0`), `tone="red"` if over the amount, `"amber"`/`"green"`
    if meaningfully under it (a lower-than-usual amount isn't necessarily bad — keep the sign
    logic simple and note it as a judgment call worth revisiting once it's in front of real data).
- Update `insight_validator`/`Insight` type in `validators.ts` to match.
- `Dashboard.svelte`'s insights list: render the left color bar (`tone`-keyed, reusing the
  existing `--red`/`--warning`/`--green`/`--accent-forecast` CSS variables rather than inventing
  new hex values), title + detail stacked, and the right-aligned `value` badge — same card
  structure the mockup shows, still linking through to `#context-{entry_hash}` as today.

**Verification:** `pytest --cov=fava --cov-fail-under=100` (rewrite `tests/test_core_insights.py`'s
assertions for the new field shape, same fixture patterns), snapshot/assertion updates in
`test_json_api.py` for `get_insights`, `svelte-check`/`eslint`/build clean, manual check against
`long-example.beancount` that both insight types render sensibly with plausible tones.

---

## Phase 18 — Suggester redesign

**Goal:** add the mockup's prominent "Accept top match" CTA button alongside the existing (and
better-UX) per-row-clickable suggestions, and restyle rows as confidence-tiered pill chips.

- Keep per-suggestion click-to-accept (already built, arguably an improvement on the mockup's
  single-CTA-only interaction) but add a prominent green "Accept top match" button above/below the
  list that calls the exact same `accept()` flow already in `Suggester.svelte` with the first
  (highest-confidence) suggestion — pure UI addition, no new logic.
- Restyle each suggestion row as a pill: tinted background/border for the top match (green-tinted,
  matching the mockup's `#16211c`/`#24463a`), neutral background for the rest, confidence bar +
  percentage kept as already built.
- Header gets the mockup's "new payee detected" subtitle (or an equivalent derived from whether
  the flagged transaction's payee is genuinely new vs. just uncategorized — reuse insights data if
  convenient, else keep it generic).

**Verification:** manual check that both "Accept top match" and clicking an individual suggestion
still correctly rewrite the transaction's account and clear the card (regression check against
Phase 8's tested flow), `svelte-check`/`eslint`/build clean.

---

## Phase 19 — Forecast tiles redesign

**Goal:** add the mockup's per-tile progress-meter bar, delta badge, and descriptive note line.

- `get_predictions()` gains a `net_worth_monthly_change` (or similar) field exposing the existing
  internal trend slope (already computed as `nw_stats.daily_change` inside `forecast.py`'s fit,
  just not surfaced) — needed for the net-worth tile's note text ("at current $X/mo trend").
- `ForecastTiles.svelte`: each tile gets a thin meter bar (fill width driven by a sensible
  normalization per tile — e.g. progress toward FI target, spend vs. a reasonable ceiling) with a
  delta badge, and a note line using the newly-exposed trend rate / existing prediction fields
  (spend-next-month's note can reference the fit window already used, cash-flow's note can say
  "income minus recurring", FI target's note can say "4% rule on projected trend" — all derivable
  from existing computation, no further backend additions needed beyond the one new field above).

**Verification:** `pytest --cov=fava --cov-fail-under=100` for the new `Predictions` field,
`svelte-check`/`eslint`/build clean, manual check that meter widths/deltas look sane against
`long-example.beancount`.

---

## Phase 20 — Shared visual language on ledger reports

**Goal:** apply the Phase 6/8 card/label/mono-number vocabulary to Journal, Balance Sheet, Income
Statement, Trial Balance, and Query — consistency pass, not a redesign (no mockup exists for
these).

- Review each report's existing markup for places that should adopt `.card`/`.card-label` (e.g.
  wrapping the Journal's filter/legend area, Balance Sheet/Income Statement/Trial Balance's
  section headers) and confirm numeric/tabular columns consistently use the monospace font (spot-
  check existing `tree-table.css`/`journal.css` — Phase 6 already re-themed colors app-wide via
  CSS variables, so this phase is about applying the newer card/spacing/typography conventions
  layered on top, not re-doing the palette work).
- Keep changes additive/low-risk — these reports have real, well-tested functionality (filtering,
  sorting, drill-down) that must not regress for the sake of visual polish.

**Verification:** manual visual pass on each of the 5 reports in both light and dark mode, full
existing test suites for these reports stay green (no functional changes expected, so any test
failure here is a signal something broke), `svelte-check`/`eslint`/`biome`/build clean.

---

## Overall verification for Part 3

Same bar as Parts 1–2: `pytest --cov=fava --cov-fail-under=100`, `ruff check`/`format`, `mypy`,
`ty check`, `svelte-check`, `eslint`, `biome check`, frontend unit test suite, and a manual
in-browser pass per phase against `long-example.beancount` (and against the mockup file directly
for Phases 12–19). Land each phase as its own commit. Given the size of this part, check in with
the user after Phase 11 (the removal phase, highest blast radius) and again after Phase 14 (the
bespoke chart, the biggest single visual swing) rather than only at the very end.
