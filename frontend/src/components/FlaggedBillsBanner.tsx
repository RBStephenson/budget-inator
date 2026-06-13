import type { AssignedBill, PayPeriod } from "../types/schedule";
import { fmtCurrency } from "../utils/currency";

interface Props {
  periods: PayPeriod[];
}

interface FlaggedEntry {
  bill: AssignedBill;
  periodPayDate: string;
}

function fmtDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function FlaggedBillsBanner({ periods }: Props) {
  const flagged: FlaggedEntry[] = periods.flatMap((p) =>
    p.assigned_bills
      .filter((b) => b.status === "late_flagged")
      .map((b) => ({ bill: b, periodPayDate: p.pay_date })),
  );

  if (flagged.length === 0) return null;

  return (
    <div className="flagged-banner" role="alert">
      <h2 className="flagged-banner__title">
        ⚠ {flagged.length} bill{flagged.length !== 1 ? "s" : ""} cannot be paid on time
      </h2>
      <ul className="flagged-banner__list">
        {flagged.map(({ bill, periodPayDate }) => (
          <li key={`${bill.bill_id}-${bill.due_date}`} className="flagged-banner__item">
            <span className="flagged-banner__name">{bill.name}</span>
            <span className="flagged-banner__meta">
              due {fmtDate(bill.due_date)} · {fmtCurrency(bill.amount)} · pay period{" "}
              {fmtDate(periodPayDate)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
