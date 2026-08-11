import { Link } from "./Link";

export function HelpPage() {
  return (
    <div className="help-page">
      <div className="page-hero page-hero--help">
        <div className="page-hero__copy">
          <Link href="/" className="back-link">← Dashboard</Link>
          <p className="page-hero__eyebrow">Help</p>
          <h2 className="page-hero__title">Budget-inator field guide</h2>
          <p className="page-hero__subtitle">
            A quick reference for setup, bill management, payment tracking, and backups.
          </p>
        </div>
        <div className="page-hero__meta">
          <span className="page-hero__pill">Readable reference</span>
        </div>
      </div>

      <div className="help-page__body">

        <section className="help-section">
          <h3 className="help-section__title">First-time setup</h3>
          <p>
            When you open Budget-inator for the first time, go to{" "}
            <strong>Settings</strong> and fill in your pay details:
          </p>
          <ul>
            <li><strong>Net salary</strong> — your take-home pay per paycheck (after tax)</li>
            <li><strong>Pay frequency</strong> — how often you get paid (weekly, bi-weekly, semi-monthly, or monthly)</li>
            <li><strong>First paycheck date</strong> — the anchor date used to compute all pay periods; use your most recent or next paycheck date</li>
            <li><strong>Current balance</strong> — what is in your account right now; used as the opening balance for the first period</li>
          </ul>
          <p>
            For semi-monthly schedules, an anchor on or before the 15th uses the
            1st/15th pattern. An anchor after the 15th uses the 15th/month-end
            pattern.
          </p>
          <p>Save, then add your bills from the dashboard or the Bills page.</p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Dashboard</h3>
          <p>
            The dashboard has two views. Toggle between them with the{" "}
            <strong>By Pay Period</strong> / <strong>By Month</strong> buttons at the top.
          </p>

          <h4 className="help-section__subtitle">By Pay Period</h4>
          <p>
            The current period appears as a hero card. Upcoming periods are listed below
            it, collapsed by default. Each card shows:
          </p>
          <ul>
            <li>Stat cards for available cash, bills due, late flags, and paid progress</li>
            <li>
              A <strong>Buffer</strong> stat card showing the running total carried from
              every already-closed pay period, tracked independently of the live
              current-period balance
            </li>
            <li>Quick Add for fast monthly bills, with a link to the full bill form</li>
            <li>Bills grouped by category with per-category subtotals</li>
            <li>
              <strong>Available to spend</strong> — opening balance minus all pending and
              paid bills. Colour coded: green (&ge;20&nbsp;% of opening balance remaining),
              amber (&lt;20&nbsp;%), red (overspent)
            </li>
            <li>A <strong>Paid so far / Still to pay</strong> dollar breakdown per period</li>
          </ul>

          <p>
            After payday, a banner asks for your actual deposit or current balance.
            Saving either value re-anchors the rolling projection from that pay date.
            You can also edit the starting balance directly on a period card.
          </p>
          <p>
            If a period has money left over, use <strong>Rebalance available funds</strong>{" "}
            to preview eligible future bills that can move into that paycheck. Applied
            moves can be reset from the bill row.
          </p>
          <p>
            Expand <strong>Past periods</strong> to review completed periods and
            retroactively mark missed payments.
          </p>

          <h4 className="help-section__subtitle">By Month</h4>
          <p>
            Shows a table of calendar months with total income, total bills, and net
            remaining. Months where bills exceed income are highlighted in red.
          </p>

          <h4 className="help-section__subtitle">Flagged bills banner</h4>
          <p>
            A red banner appears at the top when any bill cannot be paid on time — i.e.
            the pay date falls after the due date and no grace period covers the gap.
            Resolve these by adjusting the bill&apos;s grace period or overriding the
            pay date for that period. The same count also shows as a badge on the{" "}
            <strong>Dashboard</strong> link in the sidebar.
          </p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Managing bills</h3>
          <p>
            Go to <strong>Bills</strong> (via the <em>+ Add Bill</em> button or the
            Bills link). Use <strong>Edit</strong> to modify a bill,{" "}
            <strong>Duplicate</strong> to clone it, or <strong>Deactivate</strong> to
            hide it. Deactivated bills are hidden from the schedule but not
            permanently deleted. Edits use an effective date, so past schedule,
            monthly summary, and PDF history keep the bill terms that applied at
            the time.
          </p>
          <p>
            <strong>Duplicate</strong> opens the Add Bill form pre-filled with the
            source bill&apos;s values (name prefixed &quot;Copy of ...&quot;). Saving
            creates a brand-new bill; the original is never modified.
          </p>
          <p>
            Use Quick Add for common bills, or open the full form for effective dates,
            month-end due rules, grace periods, sinking funds, variable amounts, and notes.
            The bills table can be searched, filtered by category, sorted by name or
            annual cost, and expanded to show inactive bills.
          </p>
          <table className="help-table">
            <thead>
              <tr><th>Field</th><th>Notes</th></tr>
            </thead>
            <tbody>
              <tr><td>Name</td><td>Display name on the dashboard and in reports</td></tr>
              <tr><td>Amount</td><td>Regular payment amount; for variable bills this is your estimate</td></tr>
              <tr><td>Category</td><td>Housing · Utilities · Subscriptions · Insurance · Debt · Savings · Other</td></tr>
              <tr><td>Recurrence</td><td>Monthly · Bi-weekly · Weekly · Quarterly · Semi-annual · Annual · One-time</td></tr>
              <tr><td>Due day / Due date</td><td>For monthly bills enter the calendar day (1–31) or choose the last day of the month; for all others enter the specific date</td></tr>
              <tr>
                <td>Effective date</td>
                <td>
                  When editing, the date the new bill terms begin. Use payment
                  status or actual amount controls to correct one specific occurrence
                  instead.
                </td>
              </tr>
              <tr>
                <td>Grace period</td>
                <td>
                  Days after the due date you can still pay without being late. Useful when
                  the due date is advisory
                </td>
              </tr>
              <tr>
                <td>Variable amount</td>
                <td>
                  Check when the actual charge varies each cycle (e.g. utilities). The amount
                  becomes an estimate and you can enter the real charge on the dashboard
                </td>
              </tr>
              <tr>
                <td>Sinking fund</td>
                <td>
                  Reserves part of each paycheck for a large future bill so the
                  money is not shown as available to spend. Actual amounts for
                  variable bills are applied against the reserve when entered.
                </td>
              </tr>
              <tr>
                <td>Notes</td>
                <td>
                  Optional reminder text saved with the bill and included in backups.
                  Bills with notes show a small indicator on their dashboard row —
                  hover or focus it to read the note
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Tracking payments</h3>
          <p>Each bill row on the period card has three action buttons:</p>
          <ul>
            <li><strong>✓ Paid</strong> — marks the bill paid for this period; dims the row</li>
            <li><strong>— Skip</strong> — marks the bill skipped; the amount is excluded from the running balance</li>
            <li><strong>↺ Pending</strong> — resets back to pending (the default)</li>
          </ul>
          <p>Status changes apply only to that bill in that specific period.</p>
          <p>
            With a bill row focused, press <strong>P</strong> to mark it paid — the
            same action as clicking <strong>✓ Paid</strong>, without a mouse. The
            shortcut is ignored while you&apos;re typing in a nearby input.
          </p>
          <p>
            To clear an entire period at once, use <strong>Mark all paid</strong> on
            the period card. It pays every remaining pending or late-flagged bill in
            that period with today&apos;s date; already-skipped bills are left alone,
            since skipping is a deliberate choice the bulk action shouldn&apos;t
            override.
          </p>
          <p>
            When a pay period becomes past, any bills left unpaid from that period
            appear in the current period card with an{" "}
            <strong>Unpaid from previous period</strong> badge. These reminders keep
            the original due date and are not added to the current period&apos;s total
            a second time.
          </p>

          <h4 className="help-section__subtitle">Variable bill actuals</h4>
          <p>
            When a bill is variable, a tilde (~) prefix appears on the amount. Click the
            amount to open an inline input and type the real charge. The period balance
            updates immediately.
          </p>

          <h4 className="help-section__subtitle">Pay date overrides</h4>
          <p>
            Click the pencil icon next to the pay date on any period card to enter an
            actual pay date. The override applies to that period only and is used when
            flagging late bills.
          </p>
          <p>
            Use <strong>Move</strong> on a bill row to place that specific unpaid
            occurrence on a different pay date. Use <strong>Reset move</strong> to
            return it to the computed schedule.
          </p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Annual cost breakdown</h3>
          <p>
            Click <strong>Annual Cost</strong> on the dashboard to open a modal showing
            every active bill&apos;s per-payment amount and annual cost, grouped by
            category with subtotals and a grand total. A donut chart with a
            color/percentage legend breaks down annual spend by category.
          </p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">PDF report</h3>
          <p>
            Click <strong>Download PDF</strong> on the dashboard. The report contains:
          </p>
          <ul>
            <li><strong>Pay Period Schedule</strong> — each upcoming period with its bills, statuses, and available-to-spend balance</li>
            <li><strong>Monthly Summary</strong> — monthly income, total bills, sinking-fund reserves, and net remaining across the full schedule window</li>
          </ul>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Settings</h3>

          <h4 className="help-section__subtitle">Pay schedule</h4>
          <p>
            Update your net salary, pay frequency, first paycheck date, or current balance
            at any time. Changes restructure your pay periods immediately.
          </p>
          <p>
            Semi-monthly schedules follow either the 1st/15th or
            15th/month-end pattern based on the first paycheck date.
          </p>

          <h4 className="help-section__subtitle">Data management</h4>
          <ul>
            <li><strong>Export backup</strong> — downloads a JSON file with your full pay schedule, bills, effective-dated bill history, payment history, adjusted pay dates, and payday actuals</li>
            <li><strong>Import backup</strong> — restores from a backup file; this overwrites all current data</li>
            <li><strong>Delete all data</strong> — permanently removes everything and returns the app to the first-time setup state</li>
          </ul>
        </section>

      </div>
    </div>
  );
}
