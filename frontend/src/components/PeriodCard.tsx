import { useState } from "react";
import type { PayPeriod } from "../types/schedule";
import { BillRow } from "./BillRow";

interface Props {
  period: PayPeriod;
  isHero?: boolean;
  onRefetch?: () => void;
}

function fmtDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function fmtCurrency(amount: string | number): string {
  return parseFloat(String(amount)).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
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

export function PeriodCard({ period, isHero = false, onRefetch }: Props) {
  const [expanded, setExpanded] = useState(isHero);

  const color = balanceColor(period.remaining_balance, period.opening_balance);
  const isOverspent = color === "overspent";
  const hasFlagged = period.flagged_bill_count > 0;

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

  return (
    <div className={cardClass}>
      <button
        className="period-card__header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="period-card__dates">
          <span className="period-card__label">{isHero ? "Current period" : "Upcoming"}</span>
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

        <span className="period-card__chevron" aria-hidden>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {isHero && (
        <div className="period-card__progress-wrap" aria-label="bills as share of income">
          <div className="period-card__progress-fill" style={{ width: `${billPct}%` }} />
        </div>
      )}

      {expanded && (
        <div className="period-card__body">
          {period.assigned_bills.length === 0 ? (
            <p className="period-card__empty">No bills this period.</p>
          ) : (
            <ul className="period-card__bill-list">
              {period.assigned_bills.map((bill) => (
                <BillRow
                  key={`${bill.bill_id}-${bill.due_date}`}
                  bill={bill}
                  payOnDate={period.pay_date}
                  onRefetch={onRefetch}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
