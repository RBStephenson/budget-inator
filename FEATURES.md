# Budget-inator — Feature Summary

A condensed tour of what Budget-inator does. For the full walkthrough see
[docs/user-guide.md](docs/user-guide.md).

## Dashboard

- Toggle between **By Pay Period** and **By Month** views
- Current pay period as a hero card; upcoming periods listed below
- Stat cards: available cash, bills due, late flags, paid progress
- **Quick Add** for fast monthly bills, with a link to the full bill form
- Bills grouped by category within each period, with per-category subtotals
- Running balance showing **available-to-spend** (green ≥ 20%, amber < 20%,
  red = overspent)
- Sticky **flagged bills banner** when anything can't be paid on time
- **Pay date override** — adjust the pay date on any individual period
- **Bill move/reset** — move one unpaid bill occurrence to another pay date,
  reset it when needed
- Mark bills **paid / skipped / pending** inline
- **Variable bill actuals** — enter the real amount for variable bills
  directly on the period card
- **Payday actuals** — save the actual deposit or current balance after
  payday to re-anchor projections
- **Starting balance edits** directly on period cards
- **Rebalance available funds** — preview and apply moves that pull
  eligible future bills into a paycheck with leftover cash
- **Past periods** — expand completed periods to review and retroactively
  mark missed payments
- Unpaid bills from a previous period surface in the current period only,
  keeping the original due date and no duplicate total

## Bill management

- Add via Quick Add or the full bill form; edit and deactivate existing
  bills
- **Effective-dated edits** — editing a bill preserves historical name,
  amount, category, and due rule for past periods
- Search, category filter, sort by name or annual cost, optional
  show-inactive toggle
- **Sinking funds** reserve part of each paycheck for a large future bill
- Recurrences: Monthly, Bi-weekly, Weekly, Quarterly, Semi-annual, Annual,
  One-time
- Categories: Housing, Utilities, Subscriptions, Insurance, Debt, Savings,
  Other
- Optional **grace period** (days after due date still countable as on-time)
- **Variable flag** for bills whose amount changes each cycle
- Optional notes, saved with the bill and included in backups

## Reports & exports

- **Annual cost breakdown** — per-payment and annual cost for every active
  bill, grouped by category with subtotals
- **PDF report** — downloadable budget report: pay period schedule plus a
  monthly income/bills/sinking-fund/net summary
- **JSON backup** — export/import the full data set (effective-dated bill
  history, payment history, adjusted pay dates, payday actuals); delete all
  data and start fresh
