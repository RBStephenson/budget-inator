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
  const [movingBill, setMovingBill] = useState(false);
  const [manualPayDate, setManualPayDate] = useState(payOnDate);
  const { addToast } = useToast();
  const isLate = bill.status === "late_flagged";
  const isPaid = bill.status === "paid";
  const isSkipped = bill.status === "skipped";
  const isManual = bill.placement_source === "manual";
  const isCarriedOver = bill.is_carried_over;

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

  async function saveManualMove() {
    if (!manualPayDate) return;
    setSaving(true);
    try {
      await patchBillInstance(
        bill.bill_id,
        bill.due_date,
        "pending",
        undefined,
        undefined,
        manualPayDate,
      );
      setMovingBill(false);
      onRefetch?.();
    } catch {
      addToast("Could not move the bill. Please try again.", "error");
    } finally {
      setSaving(false);
    }
  }

  async function clearManualMove() {
    setSaving(true);
    try {
      await patchBillInstance(
        bill.bill_id,
        bill.due_date,
        "pending",
        undefined,
        undefined,
        null,
      );
      onRefetch?.();
    } catch {
      addToast("Could not reset the bill move. Please try again.", "error");
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
  const reserveApplied = parseFloat(bill.sinking_fund_applied) > 0;
  const displayAmount =
    bill.actual_amount && reserveApplied
      ? String(
          Math.max(
            0,
            parseFloat(bill.actual_amount) - parseFloat(bill.sinking_fund_applied),
          ).toFixed(2),
        )
      : (bill.actual_amount ?? (reserveApplied ? bill.sinking_fund_shortfall : bill.amount));

  return (
    <li
      className={[
        "bill-row",
        isLate ? "bill-row--late" : "",
        isPaid ? "bill-row--paid" : "",
        isSkipped ? "bill-row--skipped" : "",
        isCarriedOver ? "bill-row--carried" : "",
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
        {reserveApplied && (
          <span className="bill-row__meta">
            Fund applied {fmtCurrency(bill.sinking_fund_applied)}
          </span>
        )}
        {isManual && bill.manual_pay_date && (
          <span className="bill-row__meta">
            Moved to {fmt(bill.manual_pay_date)}
          </span>
        )}
        {isCarriedOver && (
          <span className="bill-row__carry-badge" aria-label="Unpaid from previous period">
            Unpaid from previous period
          </span>
        )}
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
            className="btn-icon"
            onClick={() => onEdit(bill.bill_id)}
            aria-label={`Edit bill ${bill.name}`}
            title="Edit bill"
          >
            ✏
          </button>
        )}
        {!isPaid && !isSkipped && !payingPaid && !editingActual && (
          movingBill ? (
            <span className="bill-row__paid-edit">
              <input
                className="bill-row__paid-input"
                type="date"
                value={manualPayDate}
                onChange={(e) => setManualPayDate(e.target.value)}
                aria-label="Move bill to pay date"
                autoFocus
              />
              <button
                className="btn-action btn-action--confirm"
                disabled={saving || !manualPayDate}
                onClick={saveManualMove}
                aria-label="Confirm bill move"
              >
                âœ“
              </button>
              <button
                className="btn-action"
                disabled={saving}
                onClick={() => setMovingBill(false)}
                aria-label="Cancel bill move"
              >
                âœ•
              </button>
            </span>
          ) : (
            <>
              <button
                className="btn-action"
                disabled={saving}
                onClick={() => {
                  setManualPayDate(bill.manual_pay_date ?? payOnDate);
                  setMovingBill(true);
                }}
              >
                Move
              </button>
              {isManual && (
                <button
                  className="btn-action"
                  disabled={saving}
                  onClick={clearManualMove}
                  aria-label="Reset bill move"
                >
                  Reset move
                </button>
              )}
            </>
          )
        )}
        {bill.is_variable && !isPaid && !isSkipped && !payingPaid && !movingBill && (
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
