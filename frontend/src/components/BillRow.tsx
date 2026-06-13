import { useState } from "react";
import { patchBillInstance } from "../api/billInstances";
import { useToast } from "../context/ToastContext";
import type { AssignedBill } from "../types/schedule";
import { fmtCurrency } from "../utils/currency";

interface Props {
  bill: AssignedBill;
  payOnDate: string;
  onRefetch?: () => void;
  onEdit?: (billId: number) => void;
}

function fmt(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function todayISO(): string {
  return new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

export function BillRow({ bill, payOnDate, onRefetch, onEdit }: Props) {
  const [saving, setSaving] = useState(false);
  const [editingActual, setEditingActual] = useState(false);
  const [actualInput, setActualInput] = useState("");
  const [payingPaid, setPayingPaid] = useState(false);
  const [paidDate, setPaidDate] = useState(todayISO());
  const { addToast } = useToast();
  const isLate = bill.status === "late_flagged";
  const isPaid = bill.status === "paid";
  const isSkipped = bill.status === "skipped";

  async function markAs(
    newStatus: "paid" | "skipped" | "pending",
    paidAt?: string,
  ) {
    setSaving(true);
    try {
      await patchBillInstance(bill.bill_id, bill.due_date, newStatus, undefined, paidAt);
      setPayingPaid(false);
      onRefetch?.();
    } catch {
      addToast("Could not update the bill status. Please try again.", "error");
    } finally {
      setSaving(false);
    }
  }

  async function saveActual() {
    const trimmed = actualInput.trim();
    if (!trimmed || isNaN(parseFloat(trimmed))) return;
    setSaving(true);
    try {
      await patchBillInstance(bill.bill_id, bill.due_date, "pending", trimmed);
      setEditingActual(false);
      setActualInput("");
      onRefetch?.();
    } catch {
      // Leave the editor open so the entered amount isn't lost
      addToast("Could not save the actual amount. Please try again.", "error");
    } finally {
      setSaving(false);
    }
  }

  function cancelActual() {
    setEditingActual(false);
    setActualInput("");
  }

  const isEstimated = bill.is_variable && bill.actual_amount == null;
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
      <span className="bill-row__amount">
        {isEstimated && <span className="bill-row__estimated-mark" aria-label="estimated">~</span>}
        {fmtCurrency(displayAmount)}
      </span>
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
        ) : payingPaid ? (
          <span className="bill-row__paid-edit">
            <input
              className="bill-row__paid-input"
              type="date"
              max={todayISO()}
              value={paidDate}
              onChange={(e) => setPaidDate(e.target.value)}
              aria-label="Paid date"
              autoFocus
            />
            <button
              className="btn-action btn-action--confirm"
              disabled={saving || !paidDate}
              onClick={() => markAs("paid", paidDate)}
              aria-label="Confirm paid date"
            >
              ✓
            </button>
            <button
              className="btn-action"
              disabled={saving}
              onClick={() => setPayingPaid(false)}
              aria-label="Cancel paid"
            >
              ✕
            </button>
          </span>
        ) : (
          <>
            <button
              className="btn-action btn-action--paid"
              disabled={saving}
              onClick={() => {
                setPaidDate(todayISO());
                setPayingPaid(true);
              }}
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
        {onEdit && (
          <button
            className="btn-action btn-action--edit-bill"
            onClick={() => onEdit(bill.bill_id)}
            aria-label={`Edit bill ${bill.name}`}
          >
            Edit bill
          </button>
        )}
        {bill.is_variable && !isPaid && !isSkipped && !payingPaid && (
          editingActual ? (
            <span className="bill-row__actual-edit">
              <input
                className="bill-row__actual-input"
                type="number"
                min="0"
                step="0.01"
                placeholder={bill.amount}
                value={actualInput}
                onChange={(e) => setActualInput(e.target.value)}
                aria-label="Actual amount"
                autoFocus
              />
              <button
                className="btn-action btn-action--confirm"
                disabled={saving}
                onClick={saveActual}
                aria-label="Confirm actual amount"
              >
                ✓
              </button>
              <button
                className="btn-action"
                disabled={saving}
                onClick={cancelActual}
                aria-label="Cancel actual amount"
              >
                ✕
              </button>
            </span>
          ) : (
            <button
              className="btn-action btn-action--actual"
              disabled={saving}
              onClick={() => {
                setActualInput(bill.actual_amount ?? "");
                setEditingActual(true);
              }}
              aria-label={bill.actual_amount ? "Edit actual amount" : "Enter actual amount"}
            >
              {bill.actual_amount ? "Edit actual" : "Enter actual"}
            </button>
          )
        )}
      </span>
    </li>
  );
}
