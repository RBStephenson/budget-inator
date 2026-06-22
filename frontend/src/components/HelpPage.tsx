import { Link } from "./Link";

export function HelpPage() {
  return (
    <div className="help-page">
      <div className="help-page__header">
        <Link href="/" className="back-link">← Dashboard</Link>
        <h2 className="help-page__title">Help</h2>
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
            <li>Bills grouped by category with per-category subtotals</li>
            <li>
              <strong>Available to spend</strong> — opening balance minus all pending and
              paid bills. Colour coded: green (&ge;20&nbsp;% of opening balance remaining),
              amber (&lt;20&nbsp;%), red (overspent)
            </li>
          </ul>

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
            pay date for that period.
          </p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Managing bills</h3>
          <p>
            Go to <strong>Bills</strong> (via the <em>+ Add Bill</em> button or the
            Bills link). Use the edit button to modify a bill or deactivate it.
            Deactivated bills are hidden from the schedule but not permanently deleted.
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
              <tr><td>Due day / Due date</td><td>For monthly bills enter the calendar day (1–28); for all others enter the specific date</td></tr>
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
        </section>

        <section className="help-section">
          <h3 className="help-section__title">Annual cost breakdown</h3>
          <p>
            Click <strong>Annual Cost</strong> on the dashboard to open a modal showing
            every active bill&apos;s per-payment amount and annual cost, grouped by
            category with subtotals and a grand total.
          </p>
        </section>

        <section className="help-section">
          <h3 className="help-section__title">PDF report</h3>
          <p>
            Click <strong>Download PDF</strong> on the dashboard. The report contains:
          </p>
          <ul>
            <li><strong>Pay Period Schedule</strong> — each upcoming period with its bills, statuses, and available-to-spend balance</li>
            <li><strong>Monthly Summary</strong> — monthly income, total bills, and net remaining across the full schedule window</li>
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
            <li><strong>Export backup</strong> — downloads a JSON file with your full pay schedule, bills, and payment history</li>
            <li><strong>Import backup</strong> — restores from a backup file; this overwrites all current data</li>
            <li><strong>Delete all data</strong> — permanently removes everything and returns the app to the first-time setup state</li>
          </ul>
        </section>

      </div>
    </div>
  );
}
