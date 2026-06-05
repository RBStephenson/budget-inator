import { useState } from "react";
import type { MonthlySummary } from "../types/monthly";
import { CATEGORY_LABELS } from "../types/bill";
import type { BillCategory } from "../types/bill";

interface Props {
  summary: MonthlySummary;
}

function fmtMonth(monthStr: string): string {
  const [year, month] = monthStr.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    month: "long",
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

function balanceColor(available: string, income: string): BalanceColor {
  const avail = parseFloat(available);
  const inc = parseFloat(income);
  if (avail < 0) return "overspent";
  if (inc <= 0) return "green";
  return avail / inc >= 0.2 ? "green" : "amber";
}

function fmtDay(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function MonthCard({ summary }: Props) {
  const [expanded, setExpanded] = useState(false);

  const color = balanceColor(summary.available, summary.total_income);
  const isOverspent = color === "overspent";

  const cardClass = [
    "month-card",
    isOverspent ? "month-card--overspent" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cardClass}>
      <button
        className="month-card__header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        aria-label={fmtMonth(summary.month)}
      >
        <span className="month-card__title">{fmtMonth(summary.month)}</span>

        <div className="month-card__summary">
          <div className="month-card__row">
            <span className="month-card__label">Income</span>
            <span className="month-card__value">
              {fmtCurrency(summary.total_income)}
            </span>
          </div>
          <div className="month-card__row">
            <span className="month-card__label">Bills</span>
            <span className="month-card__value">
              −{fmtCurrency(summary.total_bills)}
            </span>
          </div>
          <div className="month-card__row">
            <span className="month-card__label">
              {isOverspent ? "Overspent" : "Available"}
            </span>
            <span
              className={`month-card__value month-card__value--${color}`}
            >
              {fmtCurrency(summary.available)}
            </span>
          </div>
        </div>

        <span className="month-card__chevron" aria-hidden>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div className="month-card__body">
          {summary.categories.length === 0 ? (
            <p className="month-card__empty">No bills this month.</p>
          ) : (
            <div className="month-card__groups">
              {summary.categories.map((group) => (
                <div key={group.category} className="month-card__group">
                  <div className="month-card__group-header">
                    <h4 className="month-card__category-heading">
                      {CATEGORY_LABELS[group.category as BillCategory] ??
                        group.category}
                    </h4>
                    <span className="month-card__category-subtotal">
                      {fmtCurrency(group.subtotal)}
                    </span>
                  </div>
                  <ul className="month-card__bill-list">
                    {group.bills.map((bill) => (
                      <li
                        key={`${bill.bill_id}-${bill.due_date}`}
                        className="month-card__bill-item"
                      >
                        <span className="month-card__bill-name">
                          {bill.name}
                          {bill.is_variable && (
                            <span className="month-card__estimated"> ~</span>
                          )}
                        </span>
                        <span className="month-card__bill-due">
                          {fmtDay(bill.due_date)}
                        </span>
                        <span className="month-card__bill-amount">
                          {fmtCurrency(bill.amount)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
