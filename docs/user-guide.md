# Budget-inator User Guide

Budget-inator maps your bills to your pay schedule so you always know which bills fall in which pay period, what your balance looks like after paying them, and whether anything is at risk of being paid late.

## Table of contents

- [First-time setup](#first-time-setup)
- [Dashboard](#dashboard)
  - [By Pay Period view](#by-pay-period-view)
  - [By Month view](#by-month-view)
  - [Flagged bills banner](#flagged-bills-banner)
- [Managing bills](#managing-bills)
  - [Bill fields explained](#bill-fields-explained)
- [Tracking payments](#tracking-payments)
  - [Variable bill actuals](#variable-bill-actuals)
  - [Pay date overrides](#pay-date-overrides)
- [Annual cost breakdown](#annual-cost-breakdown)
- [PDF report](#pdf-report)
- [Settings](#settings)
  - [Pay schedule](#pay-schedule)
  - [Data management](#data-management)

---

## First-time setup

When you open Budget-inator for the first time the dashboard shows a welcome screen asking you to set up your pay schedule. Click **Set up pay schedule** (or navigate to **Settings**) and fill in:

| Field | What to enter |
|---|---|
| Net salary | Your take-home pay per paycheck (after tax) |
| Pay frequency | How often you get paid |
| First paycheck date | The date of your most recent (or next) paycheck — this anchors all period calculations. For semi-monthly pay, dates on or before the 15th use the 1st/15th pattern; dates after the 15th use 15th/month-end |
| Current balance | What is in your account right now |

Save, and you will be taken back to the dashboard where your pay periods will appear. Add your first bill with **+ Add Bill**.

---

## Dashboard

### By Pay Period view

The default view. Each pay period is shown as a card.

**Current period** — displayed as a prominent hero card with extra detail:
- Opening balance (what you had at the start of the period)
- Bills grouped by category, each with its due date, pay date, amount, and status
- A per-category subtotal row
- **Available to spend** — the opening balance minus all pending and paid bills for this period. Color coded:
  - Green — 20 % or more of the opening balance remaining
  - Amber — less than 20 % remaining
  - Red — overspent (bills exceed balance)
- **Paid so far / Still to pay** — a running dollar breakdown of the period's bills by status
- **Starting balance** — editable directly on the period card if you need to correct it
- **Rebalance available funds** — if the period has money left over, preview and apply moves that pull eligible future bills into that paycheck; a moved bill can be reset back to its computed schedule
- **Past periods** — expand a completed period to review it or retroactively mark a missed payment

A **Buffer** stat card above the hero card shows the running total carried
from every already-closed pay period (income minus that period's bills),
tracked independently of the live current-period balance — a cushion figure
separate from what any single upcoming period shows as available.

**Upcoming periods** — listed below the hero card, collapsed by default. Click any card to expand it and see the same detail.

### By Month view

Click **By Month** on the dashboard toggle. Each calendar month shows:

- Total income (paychecks landing in that month)
- Total bills assigned to that month
- Net remaining (income minus bills)

Months where bills exceed income are highlighted in red.

### Flagged bills banner

If any bill cannot be paid before its due date — because the pay date falls after the due date and no grace period covers the gap — a sticky red banner appears at the top of the dashboard listing the affected bills. Resolve these by adjusting the bill's grace period, the pay schedule, or by manually overriding the pay date for that period.

The same flagged-bill count shows as a badge on the **Dashboard** link in the sidebar, so it's visible from any page without opening the dashboard.

---

## Managing bills

Go to **Bills** (the **+ Add Bill** button on the dashboard takes you there, or navigate to `/bills`).

The bills table shows all your active bills. Use **Edit** to modify a bill, **Duplicate** to clone it, or **Deactivate** to hide it. Deactivated bills are hidden from future schedule windows but not deleted.

**Duplicate** opens the Add Bill form pre-filled with the source bill's values (name prefixed "Copy of ..."). Saving creates a brand-new bill — the original is never modified. Useful for near-identical recurring charges, like a second streaming subscription with the same billing cycle.

Bill edits are effective-dated. When you change a bill's name, amount, category, recurrence, due rule, grace period, variable flag, or active status, the app keeps the old terms for earlier occurrences and uses the new terms from the effective date forward. To correct one specific occurrence instead, use the paid/skipped/pending and actual amount controls on that bill row.

Click **+ Add Bill** to open the bill form.

### Bill fields explained

| Field | Notes |
|---|---|
| **Name** | Display name shown on the dashboard and in reports |
| **Amount** | The regular payment amount. For variable bills this is your estimate |
| **Category** | Housing · Utilities · Subscriptions · Insurance · Debt · Savings · Other |
| **Recurrence** | How often the bill repeats — see table below |
| **Due day / Due date** | For monthly bills enter the calendar day (1–31), or choose **Last day of month**. Fixed days 29–31 clamp to the final day in shorter months; the month-end option always uses that month’s final calendar day. For all other recurrences, enter the specific due date |
| **Effective date** | Shown when editing. The date the new bill terms begin; earlier occurrences keep their previous terms |
| **Sinking fund** | Check this for large quarterly, semi-annual, annual, or one-time bills. The schedule reserves part of each paycheck before the next due date so that money is not shown as available to spend |
| **Grace period** | Number of days after the due date you can still pay without being considered late. Useful for bills where the due date is advisory |
| **Variable amount** | Check this if the actual charge varies each cycle (e.g. utilities, credit cards). The amount field becomes the estimate. You can enter the real amount directly on the dashboard each period |
| **Notes** | Optional free-text reminder shown when editing the bill. Bills with notes also show a small indicator on their dashboard row — hover or focus it to read the note without opening the edit form |

**Recurrence options**

| Option | Frequency |
|---|---|
| Monthly | Once per calendar month on a fixed day |
| Bi-weekly | Every two weeks from the due date |
| Weekly | Every week from the due date |
| Quarterly | Every three months |
| Semi-annual | Twice a year |
| Annual | Once a year |
| One-time | Appears once on the due date then goes inactive |

---

## Tracking payments

Each bill row on the period card has three action buttons:

- **✓ Paid** — marks the bill as paid for this period. The row dims and a green badge appears. The bill's amount is included in the balance calculation at the actual amount if you entered one
- **— Skip** — marks the bill as skipped. The amount is excluded from the running balance for this period
- **↺ Pending** — resets the status back to pending (the default)

Status changes apply only to that bill's occurrence in that specific period. They don't affect other periods or the bill's configuration.

With a bill row focused, pressing **P** marks it paid — the same action as clicking **✓ Paid**, without a mouse. The shortcut is ignored while focus is inside a text input, so typing in a nearby field never triggers it.

To pay off an entire period in one step, use **Mark all paid** on the period card. It marks every bill still `pending`/`late_flagged` as paid with today's date in a single confirmed action; already-skipped or already-paid bills are left untouched, since skipping is a deliberate decision the bulk action shouldn't override.

When a pay period becomes past, any bills left unpaid from that period appear in the current period card with an **Unpaid from previous period** badge. These carried rows keep the original due date and are visual reminders only; the bill is not added to the current period's total a second time.

### Sinking funds

When a bill has **Build a sinking fund** enabled, Budget-inator projects the next due occurrence, calculates a per-paycheck reserve amount, and subtracts that contribution from the period's available balance. The due bill still appears on its due date, but any projected reserve is applied first and only the shortfall reduces that period's safe-to-spend amount.

For variable bills, the estimate is used until you enter an actual amount. Once an actual amount is known, the reserve is recalculated against the actual amount for that occurrence; any remaining shortfall stays visible.

### Variable bill actuals

When a bill is marked as **variable**, a tilde (~) prefix appears on the amount to indicate it is an estimate. On the period card, click the amount to open an inline input and type the real charge. Press Enter or click the checkmark to save — the period balance updates immediately.

### Pay date overrides

The pay date shown on each period card is computed from your pay schedule. If a paycheck lands on a different date (bank holiday, early deposit), click the **pencil icon** next to the pay date, enter the actual date, and confirm. The override applies to that period only and is used when determining whether any bills are flagged as late.

---

## Annual cost breakdown

Click **Annual Cost** on the dashboard to open a modal showing every active bill's:

- Per-payment amount (estimate shown with ~ for variable bills)
- Annual cost (amount × payments per year)

A donut chart at the top breaks down annual spend by category, with a legend showing each category's color, dollar total, and percentage of the whole. Below it, bills are grouped by category with a subtotal per category and a grand total at the bottom. Useful for reviewing your total annual spend at a glance.

---

## PDF report

Click **Download PDF** on the dashboard. The report contains two sections:

1. **Pay Period Schedule** — each upcoming pay period with its bills, statuses, and available-to-spend balance, matching what you see on the dashboard
2. **Monthly Summary** — a table of monthly income, total bills, and net remaining across the full schedule window

The report is generated from the current data at the time you click the button. Months with a negative net remaining are highlighted in red.

---

## Settings

### Pay schedule

Navigate to **Settings** from the top navigation bar.

| Field | Notes |
|---|---|
| Net salary | Your take-home pay per paycheck |
| Pay frequency | Weekly · Bi-weekly · Semi-monthly · Monthly |
| First paycheck date | Anchor date — all periods are computed forward and backward from this date. Semi-monthly anchors on or before the 15th use 1st/15th; anchors after the 15th use 15th/month-end |
| Current balance | What is in your account right now. Used as the opening balance for the first period |

Changes take effect immediately when saved. Updating the pay frequency or first paycheck date will restructure all your pay periods and re-assign bills.

### Data management

Found at the bottom of the Settings page.

**Export backup** — downloads a `budget-inator-backup-YYYY-MM-DD.json` file containing your full pay schedule, all bills, effective-dated bill history, all bill instance overrides (payment statuses and actual amounts), and adjusted pay dates. Keep this somewhere safe if you ever need to migrate or recover.

**Import backup** — restores from a backup file. This **overwrites all current data** and cannot be undone. Import is intended for migration and recovery, not for merging two data sets.

**Delete all data** — permanently removes your pay schedule, all bills, and all history. You will be prompted to confirm. The app returns to the first-time setup state.
