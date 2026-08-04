import { useState } from "react";
import type { PayPeriod } from "../types/schedule";
import { CATEGORY_LABELS, CATEGORY_ORDER } from "../types/bill";
import { BillRow } from "./BillRow";
import { listPayPeriodActuals, putPayPeriodActual } from "../api/payPeriodActuals";
import { putPayPeriodOverride, deletePayPeriodOverride } from "../api/payPeriodOverrides";
import { applyRebalance, previewRebalance } from "../api/rebalance";
import { ConfirmDialog } from "./ConfirmDialog";
import { useToast } from "../context/ToastContext";
import { fmtCurrency } from "../utils/currency";
import type { RebalancePreview } from "../types/schedule";

interface Props {
  period: PayPeriod;
  isHero?: boolean;
  onRefetch?: () => void;
  onEditBill?: (billId: number) => void;
  /** Overrides the header label (defaults to "Current period"/"Upcoming"). */
  label?: string;
}

function fmtDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function fmtDateShort(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

type BalanceColor = "green" | "amber" | "overspent";

function balanceColor(remaining: string, opening: string): BalanceColor {
  const rem = parseFloat(remaining);
  const open = parseFloat(opening);
  if (rem < 0) return "overspent";
  if (open <= 0) return "green";
  return rem / open >= 0.2 ? "green" : "amber";
}

export function PeriodCard({ period, isHero = false, onRefetch, onEditBill, label }: Props) {
  const headerLabel = label ?? (isHero ? "Current period" : "Upcoming");
  const [expanded, setExpanded] = useState(isHero);
  const [editingPayDate, setEditingPayDate] = useState(false);
  const [payDateInput, setPayDateInput] = useState("");
  const [savingPayDate, setSavingPayDate] = useState(false);
  const [editingOpeningBalance, setEditingOpeningBalance] = useState(false);
  const [openingBalanceInput, setOpeningBalanceInput] = useState("");
  const [savingOpeningBalance, setSavingOpeningBalance] = useState(false);
  const [rebalancePreview, setRebalancePreview] = useState<RebalancePreview | null>(null);
  const [rebalanceLoading, setRebalanceLoading] = useState(false);
  const { addToast } = useToast();

  const color = balanceColor(period.remaining_balance, period.opening_balance);
  const isOverspent = color === "overspent";
  const hasFlagged = period.flagged_bill_count > 0;
  const manualMoveCount = period.assigned_bills.filter(
    (bill) => bill.placement_source === "manual",
  ).length;
  const hasManualMoves = manualMoveCount > 0;

  const cardClass = [
    "period-card",
    isHero ? "period-card--hero" : "period-card--upcoming",
    isOverspent ? "period-card--overspent" : "",
    hasFlagged && !isOverspent ? "period-card--has-flagged" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const opening = parseFloat(period.opening_balance);
  const billPct =
    opening > 0 ? Math.min((parseFloat(period.total_bills) / opening) * 100, 100) : 0;

  const todayStr = new Date().toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  async function savePayDateOverride() {
    if (!payDateInput) return;
    setSavingPayDate(true);
    try {
      await putPayPeriodOverride(period.original_pay_date, payDateInput);
      setEditingPayDate(false);
      setPayDateInput("");
      onRefetch?.();
    } catch {
      addToast("Could not update the pay date. Please try again.", "error");
    } finally {
      setSavingPayDate(false);
    }
  }

  async function clearPayDateOverride() {
    setSavingPayDate(true);
    try {
      await deletePayPeriodOverride(period.original_pay_date);
      onRefetch?.();
    } catch {
      addToast("Could not reset the pay date. Please try again.", "error");
    } finally {
      setSavingPayDate(false);
    }
  }

  function startOpeningBalanceEdit() {
    setOpeningBalanceInput(String(parseFloat(period.opening_balance)));
    setEditingOpeningBalance(true);
  }

  function cancelOpeningBalanceEdit() {
    setEditingOpeningBalance(false);
    setOpeningBalanceInput("");
  }

  async function saveOpeningBalance() {
    const nextBalance = parseFloat(openingBalanceInput);
    if (openingBalanceInput.trim() === "" || isNaN(nextBalance) || nextBalance < 0) {
      addToast("Enter a starting balance of 0 or more.", "error");
      return;
    }

    setSavingOpeningBalance(true);
    try {
      const actuals = await listPayPeriodActuals();
      const existing = actuals.find((actual) => actual.pay_date === period.original_pay_date);
      await putPayPeriodActual(period.original_pay_date, {
        actualNetPay: existing?.actual_net_pay ?? undefined,
        actualBalance: openingBalanceInput,
      });
      setEditingOpeningBalance(false);
      setOpeningBalanceInput("");
      addToast("Starting balance updated.", "success");
      onRefetch?.();
    } catch {
      addToast("Could not update the starting balance. Please try again.", "error");
    } finally {
      setSavingOpeningBalance(false);
    }
  }

  async function openRebalancePreview() {
    setRebalanceLoading(true);
    try {
      const preview = await previewRebalance(period.original_pay_date);
      setRebalancePreview(preview);
    } catch {
      addToast("Could not preview rebalance moves. Please try again.", "error");
    } finally {
      setRebalanceLoading(false);
    }
  }

  async function confirmRebalance() {
    if (!rebalancePreview || rebalancePreview.moves.length === 0) {
      setRebalancePreview(null);
      return;
    }
    setRebalanceLoading(true);
    try {
      await applyRebalance(rebalancePreview.moves);
      setRebalancePreview(null);
      onRefetch?.();
    } catch {
      addToast("Could not apply rebalance moves. Please try again.", "error");
    } finally {
      setRebalanceLoading(false);
    }
  }

  function cancelPayDateEdit() {
    setEditingPayDate(false);
    setPayDateInput("");
  }

  return (
    <div className={cardClass}>
      <button
        className="period-card__header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="period-card__dates">
          <span className="period-card__label">{headerLabel}</span>
          <div className="period-card__range-line">
            <span className="period-card__range">
              {fmtDate(period.period_start)} – {fmtDate(period.period_end)}
            </span>
            {isHero && (
              <span className="period-card__today-badge" aria-label="today's date">
                {todayStr}
              </span>
            )}
          </div>
        </div>

        <div className="period-card__summary">
          <div className="period-card__balance-row">
            <span className="period-card__balance-label">Opens</span>
            <span className="period-card__balance-value">
              {fmtCurrency(period.opening_balance)}
            </span>
          </div>
          <div className="period-card__balance-row">
            <span className="period-card__balance-label">Bills</span>
            <span className="period-card__balance-value">
              −{fmtCurrency(period.total_bills)}
            </span>
          </div>
          {parseFloat(period.total_sinking_funds) > 0 && (
            <div className="period-card__balance-row">
              <span className="period-card__balance-label">Sinking funds</span>
              <span className="period-card__balance-value">
                -{fmtCurrency(period.total_sinking_funds)}
              </span>
            </div>
          )}
          <div className="period-card__balance-row">
            <span className="period-card__balance-label">
              {isOverspent ? "Overspent" : "Available"}
            </span>
            <span className={`period-card__balance-value period-card__balance-value--${color}`}>
              {fmtCurrency(period.remaining_balance)}
            </span>
          </div>
        </div>

        {hasFlagged && (
          <span
            className="period-card__flag-badge"
            aria-label={`${period.flagged_bill_count} late bill(s)`}
          >
            ⚠ {period.flagged_bill_count}
          </span>
        )}

        {hasManualMoves && (
          <span
            className="period-card__move-badge"
            aria-label={`${manualMoveCount} manually moved bill(s)`}
          >
            Moved {manualMoveCount}
          </span>
        )}

        <span className="period-card__chevron" aria-hidden>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {isHero && (
        <div className="period-card__progress-wrap" aria-label="bills as share of income">
          <div className="period-card__progress-fill" style={{ width: `${billPct}%` }} />
        </div>
      )}

      <div className="period-card__payday-row">
        <span className="period-card__payday-label">Payday</span>
        {editingPayDate ? (
          <span className="period-card__payday-edit">
            <input
              className="period-card__payday-input"
              type="date"
              value={payDateInput}
              onChange={(e) => setPayDateInput(e.target.value)}
              aria-label="Override pay date"
              autoFocus
            />
            <button
              className="btn-action btn-action--confirm"
              disabled={savingPayDate || !payDateInput}
              onClick={savePayDateOverride}
              aria-label="Confirm pay date override"
            >
              ✓
            </button>
            <button
              className="btn-action"
              disabled={savingPayDate}
              onClick={cancelPayDateEdit}
              aria-label="Cancel pay date edit"
            >
              ✕
            </button>
          </span>
        ) : (
          <span className="period-card__payday-value">
            {fmtDateShort(period.pay_date)}
            {period.is_overridden && (
              <span className="period-card__payday-adjusted" aria-label="pay date adjusted">
                adjusted
              </span>
            )}
            <button
              className="btn-icon"
              onClick={(e) => {
                e.stopPropagation();
                setPayDateInput(period.pay_date);
                setEditingPayDate(true);
              }}
              aria-label="Edit pay date"
              disabled={savingPayDate}
            >
              ✏
            </button>
            {period.is_overridden && (
              <button
                className="btn-icon btn-icon--reset"
                onClick={(e) => {
                  e.stopPropagation();
                  clearPayDateOverride();
                }}
                aria-label="Reset pay date to computed"
                disabled={savingPayDate}
              >
                ↺
              </button>
            )}
          </span>
        )}
      </div>

      <div className="period-card__opening-row">
        <span className="period-card__opening-label">Starting balance</span>
        {editingOpeningBalance ? (
          <span className="period-card__opening-edit">
            <input
              className="period-card__opening-input"
              type="number"
              min="0"
              step="0.01"
              value={openingBalanceInput}
              onChange={(e) => setOpeningBalanceInput(e.target.value)}
              aria-label="Starting balance"
              autoFocus
            />
            <button
              className="btn-action btn-action--confirm"
              disabled={savingOpeningBalance}
              onClick={saveOpeningBalance}
              aria-label="Confirm starting balance"
            >
              ✓
            </button>
            <button
              className="btn-action"
              disabled={savingOpeningBalance}
              onClick={cancelOpeningBalanceEdit}
              aria-label="Cancel starting balance edit"
            >
              ✕
            </button>
          </span>
        ) : (
          <span className="period-card__opening-value">
            {fmtCurrency(period.opening_balance)}
            <button
              className="btn-icon"
              onClick={startOpeningBalanceEdit}
              aria-label="Edit starting balance"
              disabled={savingOpeningBalance}
            >
              ✏
            </button>
          </span>
        )}
      </div>

      {hasManualMoves && (
        <div className="period-card__manual-move-row">
          <span>
            {manualMoveCount} bill{manualMoveCount === 1 ? "" : "s"} manually moved
          </span>
        </div>
      )}

      {parseFloat(period.remaining_balance) > 0 && (
        <div className="period-card__rebalance-row">
          <button
            className="btn btn--secondary"
            onClick={openRebalancePreview}
            disabled={rebalanceLoading}
          >
            {rebalanceLoading ? "Checking..." : "Rebalance available funds"}
          </button>
        </div>
      )}

      {expanded && (
        <div className="period-card__body">
          {period.assigned_bills.length === 0 ? (
            <p className="period-card__empty">No bills this period.</p>
          ) : (
            <div className="period-card__bill-groups">
              {CATEGORY_ORDER.filter((cat) =>
                period.assigned_bills.some((b) => b.category === cat),
              ).map((cat) => (
                <div key={cat} className="period-card__bill-group">
                  <h4 className="period-card__category-heading">
                    {CATEGORY_LABELS[cat]}
                  </h4>
                  <ul className="period-card__bill-list">
                    {period.assigned_bills
                      .filter((b) => b.category === cat)
                      .map((bill) => (
                        <BillRow
                          key={`${bill.bill_id}-${bill.due_date}`}
                          bill={bill}
                          payOnDate={period.pay_date}
                          onRefetch={onRefetch}
                          onEdit={onEditBill}
                        />
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
          {period.sinking_fund_contributions.length > 0 && (
            <div className="period-card__bill-group">
              <h4 className="period-card__category-heading">Sinking funds</h4>
              <ul className="period-card__bill-list">
                {period.sinking_fund_contributions.map((fund) => (
                  <li
                    key={`${fund.bill_id}-${fund.next_due_date}`}
                    className="bill-row"
                  >
                    <span className="bill-row__main">
                      <span className="bill-row__name">{fund.name}</span>
                      <span className="bill-row__meta">
                        Next due {fmtDateShort(fund.next_due_date)} · saved{" "}
                        {fmtCurrency(fund.saved_amount)} of{" "}
                        {fmtCurrency(fund.target_amount)}
                      </span>
                    </span>
                    <span className="bill-row__amount">
                      {fmtCurrency(fund.contribution_amount)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {rebalancePreview && (
        <ConfirmDialog
          title="Rebalance available funds"
          message={
            rebalancePreview.moves.length === 0
              ? "No eligible future bills can move into this period right now."
              : `Available changes from ${fmtCurrency(
                  rebalancePreview.source_remaining_before,
                )} to ${fmtCurrency(rebalancePreview.source_remaining_after)}.`
          }
          confirmLabel={rebalancePreview.moves.length === 0 ? "Done" : "Apply moves"}
          onConfirm={confirmRebalance}
          onCancel={() => setRebalancePreview(null)}
          confirmDisabled={rebalanceLoading}
        >
          {rebalancePreview.moves.length > 0 && (
            <ul className="rebalance-dialog__moves">
              {rebalancePreview.moves.map((move) => (
                <li key={`${move.bill_id}-${move.due_date}`}>
                  <span className="rebalance-dialog__move-icon" aria-hidden="true">↔</span>
                  <strong>{move.name}</strong>
                  <span>
                    {fmtDateShort(move.from_pay_date)} to{" "}
                    {fmtDateShort(move.to_pay_date)} · {fmtCurrency(move.amount)}
                  </span>
                  <small>{move.reason}</small>
                </li>
              ))}
            </ul>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}
