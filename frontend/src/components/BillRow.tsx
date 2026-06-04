import type { AssignedBill } from "../types/schedule";

interface Props {
  bill: AssignedBill;
  payOnDate: string;
}

function fmt(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function fmtCurrency(amount: string): string {
  return parseFloat(amount).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}

export function BillRow({ bill, payOnDate }: Props) {
  const isLate = bill.status === "late_flagged";

  return (
    <li className={`bill-row${isLate ? " bill-row--late" : ""}`}>
      <span className="bill-row__name">
        {isLate && (
          <span className="bill-row__late-badge" aria-label="Late — cannot be paid on time">
            ⚠
          </span>
        )}
        {bill.name}
      </span>
      <span className="bill-row__dates">
        <span className="bill-row__date-label">Due</span>
        <span className="bill-row__date-value">{fmt(bill.due_date)}</span>
        <span className="bill-row__date-label">Pay</span>
        <span className="bill-row__date-value">{fmt(payOnDate)}</span>
      </span>
      <span className="bill-row__amount">{fmtCurrency(bill.amount)}</span>
    </li>
  );
}
