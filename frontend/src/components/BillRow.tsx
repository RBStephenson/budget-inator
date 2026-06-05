import { useState } from "react";
import { patchBillInstance } from "../api/billInstances";
import type { AssignedBill } from "../types/schedule";

interface Props {
  bill: AssignedBill;
  payOnDate: string;
  onRefetch?: () => void;
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

export function BillRow({ bill, payOnDate, onRefetch }: Props) {
  const [saving, setSaving] = useState(false);
  const isLate = bill.status === "late_flagged";
  const isPaid = bill.status === "paid";
  const isSkipped = bill.status === "skipped";

  async function markAs(newStatus: "paid" | "skipped" | "pending") {
    setSaving(true);
    try {
      await patchBillInstance(bill.bill_id, bill.due_date, newStatus);
      onRefetch?.();
    } finally {
      setSaving(false);
    }
  }

  const displayAmount = bill.actual_amount ?? bill.amount;

  return (
    <li
      className={[
        "bill-row",
        isLate ? "bill-row--late" : "",
        isPaid ? "bill-row--paid" : "",
        isSkipped ? "bill-row--skipped" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span className="bill-row__name">
        {isLate && (
          <span className="bill-row__late-badge" aria-label="Late — cannot be paid on time">
            ⚠
          </span>
        )}
        {isPaid && <span className="bill-row__status-badge bill-row__status-badge--paid">✓</span>}
        {isSkipped && <span className="bill-row__status-badge bill-row__status-badge--skipped">—</span>}
        {bill.name}
      </span>
      <span className="bill-row__dates">
        <span className="bill-row__date-label">Due</span>
        <span className="bill-row__date-value">{fmt(bill.due_date)}</span>
        <span className="bill-row__date-label">Pay</span>
        <span className="bill-row__date-value">{fmt(payOnDate)}</span>
      </span>
      <span className="bill-row__amount">{fmtCurrency(displayAmount)}</span>
      <span className="bill-row__actions">
        {isPaid || isSkipped ? (
          <button
            className="btn-action"
            disabled={saving}
            onClick={() => markAs("pending")}
            aria-label="Undo"
          >
            Undo
          </button>
        ) : (
          <>
            <button
              className="btn-action btn-action--paid"
              disabled={saving}
              onClick={() => markAs("paid")}
            >
              Paid
            </button>
            <button
              className="btn-action btn-action--skip"
              disabled={saving}
              onClick={() => markAs("skipped")}
            >
              Skip
            </button>
          </>
        )}
      </span>
    </li>
  );
}
