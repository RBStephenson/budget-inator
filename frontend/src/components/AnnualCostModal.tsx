import { Fragment, useEffect, useState } from "react";
import { listBills } from "../api/bills";
import type { Bill, BillCategory } from "../types/bill";
import { CATEGORY_COLORS, CATEGORY_LABELS, CATEGORY_ORDER, annualCost } from "../types/bill";
import { fmtCurrency } from "../utils/currency";
import { CategoryPieChart } from "./CategoryPieChart";

interface Props {
  onClose: () => void;
}

export function AnnualCostModal({ onClose }: Props) {
  const [bills, setBills] = useState<Bill[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    listBills()
      .then((data) => setBills(data.filter((b) => b.is_active).sort((a, b) => a.name.localeCompare(b.name))))
      .catch(() => setError(true));
  }, []);

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  let content: React.ReactNode;
  if (error) {
    content = <p className="annual-cost__state">Could not load bills.</p>;
  } else if (bills === null) {
    content = <p className="annual-cost__state">Loading…</p>;
  } else if (bills.length === 0) {
    content = <p className="annual-cost__state">No active bills.</p>;
  } else {
    const byCategory: Partial<Record<BillCategory, Bill[]>> = {};
    for (const bill of bills) {
      (byCategory[bill.category] ??= []).push(bill);
    }
    const grandTotal = bills.reduce((sum, b) => sum + annualCost(b), 0);

    const chartSegments = CATEGORY_ORDER.filter((cat) => byCategory[cat]?.length).map((cat) => ({
      key: cat,
      label: CATEGORY_LABELS[cat],
      value: byCategory[cat]!.reduce((sum, b) => sum + annualCost(b), 0),
      color: CATEGORY_COLORS[cat],
    }));

    const table = (
      <table className="annual-cost__table">
        <thead>
          <tr>
            <th>Bill</th>
            <th className="annual-cost__num">Per payment</th>
            <th className="annual-cost__num">Annual</th>
          </tr>
        </thead>
        <tbody>
          {CATEGORY_ORDER.map((cat) => {
            const group = byCategory[cat];
            if (!group?.length) return null;
            const catTotal = group.reduce((sum, b) => sum + annualCost(b), 0);
            return (
              <Fragment key={cat}>
                <tr className="annual-cost__cat-row">
                  <td colSpan={3}>{CATEGORY_LABELS[cat]}</td>
                </tr>
                {group.map((b) => (
                  <tr key={b.id} className="annual-cost__bill-row">
                    <td>{b.name}</td>
                    <td className="annual-cost__num">
                      {b.is_variable ? "~" : ""}{fmtCurrency(parseFloat(b.amount))}
                    </td>
                    <td className="annual-cost__num">{fmtCurrency(annualCost(b))}</td>
                  </tr>
                ))}
                <tr className="annual-cost__sub-row">
                  <td colSpan={2}>Subtotal</td>
                  <td className="annual-cost__num">{fmtCurrency(catTotal)}</td>
                </tr>
              </Fragment>
            );
          })}
          <tr className="annual-cost__total-row">
            <td colSpan={2}>Total annual cost</td>
            <td className="annual-cost__num">{fmtCurrency(grandTotal)}</td>
          </tr>
        </tbody>
      </table>
    );

    content = (
      <>
        <CategoryPieChart segments={chartSegments} />
        {table}
      </>
    );
  }

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Annual cost breakdown"
      onClick={handleOverlayClick}
    >
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title">Annual Cost Breakdown</h2>
          <button className="modal__close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="annual-cost__body">
          {content}
        </div>
      </div>
    </div>
  );
}
