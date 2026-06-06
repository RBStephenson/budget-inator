import { useState } from "react";
import type { Bill, BillCategory } from "../types/bill";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  RECURRENCE_LABELS,
  annualCost,
} from "../types/bill";

interface Props {
  bills: Bill[];
  onEdit: (bill: Bill) => void;
  onDeactivate: (bill: Bill) => void;
}

type SortKey = "name" | "annual_cost";

function fmtCurrency(n: number): string {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function fmtDue(bill: Bill): string {
  if (bill.recurrence === "monthly") return `Day ${bill.due_day}`;
  if (!bill.due_date) return "—";
  return new Date(bill.due_date + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function BillTable({ bills, onEdit, onDeactivate }: Props) {
  const [sort, setSort] = useState<SortKey>("name");
  const [showInactive, setShowInactive] = useState(false);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<BillCategory | "">("");

  function applyFilters(list: Bill[]): Bill[] {
    const q = search.trim().toLowerCase();
    return list.filter((b) => {
      if (q && !b.name.toLowerCase().includes(q)) return false;
      if (categoryFilter && b.category !== categoryFilter) return false;
      return true;
    });
  }

  function sorted(list: Bill[]): Bill[] {
    return [...list].sort((a, b) => {
      if (sort === "annual_cost") return annualCost(b) - annualCost(a);
      return a.name.localeCompare(b.name);
    });
  }

  const active = bills.filter((b) => b.is_active);
  const inactive = bills.filter((b) => !b.is_active);

  const filteredActive = sorted(applyFilters(active));
  const filteredInactive = sorted(applyFilters(inactive));

  const hasFilter = search.trim() !== "" || categoryFilter !== "";
  const totalAnnual = filteredActive.reduce((sum, b) => sum + annualCost(b), 0);

  function clearFilters() {
    setSearch("");
    setCategoryFilter("");
  }

  return (
    <div className="bill-table-wrap">
      <div className="bill-table-controls">
        <input
          className="bill-table-search"
          type="search"
          placeholder="Search bills…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search bills"
        />

        <select
          className="bill-table-category-filter"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as BillCategory | "")}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {CATEGORY_ORDER.map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>

        {hasFilter && (
          <button className="btn-clear-filters" onClick={clearFilters}>
            Clear filters
          </button>
        )}

        <span className="bill-table-controls__label">Sort by</span>
        <button
          className={`btn-sort${sort === "name" ? " btn-sort--active" : ""}`}
          onClick={() => setSort("name")}
        >
          Name
        </button>
        <button
          className={`btn-sort${sort === "annual_cost" ? " btn-sort--active" : ""}`}
          onClick={() => setSort("annual_cost")}
        >
          Annual cost
        </button>
      </div>

      <table className="bill-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Amount</th>
            <th>Annual cost</th>
            <th>Recurrence</th>
            <th>Due</th>
            <th>Grace</th>
            <th>Variable</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filteredActive.length === 0 ? (
            <tr>
              <td colSpan={9} className="bill-table__empty">
                {hasFilter ? "No bills match the current filters." : "No active bills."}
              </td>
            </tr>
          ) : (
            filteredActive.map((bill) => (
              <tr key={bill.id}>
                <td className="bill-table__name">{bill.name}</td>
                <td>{CATEGORY_LABELS[bill.category]}</td>
                <td className="bill-table__num">
                  {fmtCurrency(parseFloat(bill.amount))}
                  {bill.is_variable && (
                    <span className="bill-table__estimated"> est.</span>
                  )}
                </td>
                <td className="bill-table__num">{fmtCurrency(annualCost(bill))}</td>
                <td>{RECURRENCE_LABELS[bill.recurrence]}</td>
                <td>{fmtDue(bill)}</td>
                <td className="bill-table__num">
                  {bill.grace_period_days > 0 ? `${bill.grace_period_days}d` : "—"}
                </td>
                <td className="bill-table__center">
                  {bill.is_variable ? "Yes" : "—"}
                </td>
                <td className="bill-table__actions">
                  <button
                    className="btn-action"
                    onClick={() => onEdit(bill)}
                    aria-label={`Edit ${bill.name}`}
                  >
                    Edit
                  </button>
                  <button
                    className="btn-action btn-action--danger"
                    onClick={() => onDeactivate(bill)}
                    aria-label={`Deactivate ${bill.name}`}
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3} className="bill-table__footer-label">
              Total annual cost ({filteredActive.length} bill{filteredActive.length !== 1 ? "s" : ""}
              {hasFilter ? ", filtered" : ""})
            </td>
            <td className="bill-table__num bill-table__footer-total">
              {fmtCurrency(totalAnnual)}
            </td>
            <td colSpan={5}></td>
          </tr>
        </tfoot>
      </table>

      {(filteredInactive.length > 0 || (!hasFilter && inactive.length > 0)) && (
        <div className="bill-table__inactive">
          <button
            className="btn-toggle"
            onClick={() => setShowInactive((v) => !v)}
            aria-expanded={showInactive}
          >
            {showInactive ? "▲" : "▼"} Inactive bills (
            {hasFilter ? `${filteredInactive.length} of ${inactive.length}` : inactive.length})
          </button>
          {showInactive && (
            <table className="bill-table bill-table--inactive">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Recurrence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredInactive.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="bill-table__empty">
                      No inactive bills match the current filters.
                    </td>
                  </tr>
                ) : (
                  filteredInactive.map((bill) => (
                    <tr key={bill.id}>
                      <td className="bill-table__name">{bill.name}</td>
                      <td>{CATEGORY_LABELS[bill.category]}</td>
                      <td className="bill-table__num">
                        {fmtCurrency(parseFloat(bill.amount))}
                      </td>
                      <td>{RECURRENCE_LABELS[bill.recurrence]}</td>
                      <td className="bill-table__actions">
                        <button
                          className="btn-action"
                          onClick={() => onEdit(bill)}
                          aria-label={`Edit ${bill.name}`}
                        >
                          Reactivate / Edit
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
