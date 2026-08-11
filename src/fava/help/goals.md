# Goals

Savings and payoff goals can be added via `custom` directives in the
Beancount file:

<pre><textarea is="beancount-textarea">
2026-01-01 custom "goal" Assets:Savings:House      "House fund"    50000.00 USD 2028-06-01
2026-01-01 custom "goal" Liabilities:CreditCard    "Pay off card"      0.00 USD 2027-01-01
2026-01-01 custom "goal" Assets:Savings:Emergency  "Emergency fund" 10000.00 USD</textarea></pre>

Each directive has an account, a label, a target amount, and an optional
target date. Multiple goals can point at the same account, and an account
does not need a goal to appear anywhere else in the ledger.

## Savings vs. payoff goals

If the account is one of your liability accounts, the goal is treated as a
**payoff goal**: progress is measured from the account's balance on the date
the goal was declared down to the target amount (usually `0.00`, for "fully
paid off"), rather than from zero up to the target. Any other account is
treated as a **savings goal**, where progress runs from zero up to the
target amount directly.

## Progress and ETA

Each goal shows its current balance, percent complete, and - if a target
date was given - whether it is on track. The ETA is a simple linear
projection from the account's recent balance history (the same kind of
trend fit used for the net worth forecast on the Overview page), so it can
say "no ETA yet" if the account's recent trend is not headed toward the
target, or if there is not enough history to fit a trend at all.

Goals show all-time progress and are not affected by the app's normal
`time`/`account`/`filter` controls - narrowing those to look at a different
report does not change what a goal shows.
