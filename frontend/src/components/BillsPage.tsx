import { useState } from "react";
import { deactivateBill } from "../api/bills";
import { useBills } from "../hooks/useBills";
import type { Bill } from "../types/bill";
import { BillFormModal } from "./BillFormModal";
import { BillTable } from "./BillTable";
import { ConfirmDialog } from "./ConfirmDialog";
import { Link } from "./Link";

export function BillsPage() {
  const { bills, status, refetch } = useBills();
  const [editBill, setEditBill] = useState<Bill | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [deactivateTarget, setDeactivateTarget] = useState<Bill | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  async function handleDeactivateConfirm() {
    if (!deactivateTarget) return;
    setDeactivating(true);
    try {
      await deactivateBill(deactivateTarget.id);
      setDeactivateTarget(null);
      refetch();
    } finally {
      setDeactivating(false);
    }
  }

  function handleSave() {
    setAddOpen(false);
    setEditBill(null);
    refetch();
  }

  return (
    <div className="bills-page">
      <div className="bills-page__header">
        <div>
          <Link href="/" className="back-link">← Dashboard</Link>
          <h2 className="bills-page__title">Bills</h2>
        </div>
        <button className="btn btn--primary" onClick={() => setAddOpen(true)}>
          + Add Bill
        </button>
      </div>

      {status === "loading" && (
        <p className="dashboard__state">Loading bills…</p>
      )}

      {status === "error" && (
        <p className="dashboard__state dashboard__state--error">
          Could not load bills. Make sure the API is running.
        </p>
      )}

      {status === "ok" && bills.length === 0 && (
        <p className="dashboard__state">
          No bills yet. Add one to get started.
        </p>
      )}

      {status === "ok" && bills.length > 0 && (
        <BillTable
          bills={bills}
          onEdit={setEditBill}
          onDeactivate={setDeactivateTarget}
        />
      )}

      {(addOpen || editBill) && (
        <BillFormModal
          bill={editBill ?? undefined}
          onSave={handleSave}
          onClose={() => { setAddOpen(false); setEditBill(null); }}
        />
      )}

      {deactivateTarget && (
        <ConfirmDialog
          message={`Deactivate "${deactivateTarget.name}"? It will be hidden from the schedule.`}
          confirmLabel={deactivating ? "Deactivating…" : "Deactivate"}
          onConfirm={handleDeactivateConfirm}
          onCancel={() => setDeactivateTarget(null)}
        />
      )}
    </div>
  );
}
