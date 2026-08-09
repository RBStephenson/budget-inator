import { useState } from "react";
import { deactivateBill } from "../api/bills";
import { useToast } from "../context/ToastContext";
import { useBills } from "../hooks/useBills";
import type { Bill } from "../types/bill";
import { BillFormModal } from "./BillFormModal";
import { BillTable } from "./BillTable";
import { ConfirmDialog } from "./ConfirmDialog";
import { Link } from "./Link";
import { QuickAddBar } from "./QuickAddBar";

export function BillsPage() {
  const { bills, status, refetch } = useBills();
  const [editBill, setEditBill] = useState<Bill | null>(null);
  const [duplicateSource, setDuplicateSource] = useState<Bill | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [deactivateTarget, setDeactivateTarget] = useState<Bill | null>(null);
  const [deactivating, setDeactivating] = useState(false);
  const { addToast } = useToast();

  async function handleDeactivateConfirm() {
    if (!deactivateTarget) return;
    setDeactivating(true);
    try {
      await deactivateBill(deactivateTarget.id);
      setDeactivateTarget(null);
      refetch();
    } catch {
      // Keep the dialog open so the user can retry or cancel
      addToast(
        `Could not deactivate "${deactivateTarget.name}". Please try again.`,
        "error",
      );
    } finally {
      setDeactivating(false);
    }
  }

  function handleSave() {
    setAddOpen(false);
    setEditBill(null);
    setDuplicateSource(null);
    refetch();
  }

  return (
    <div className="bills-page">
      <div className="page-hero page-hero--bills">
        <div className="page-hero__copy">
          <Link href="/" className="back-link">← Dashboard</Link>
          <p className="page-hero__eyebrow">Bill list</p>
          <h2 className="page-hero__title">Your recurring money map</h2>
          <p className="page-hero__subtitle">
            Manage due dates, recurrence, estimates, and sinking funds in one roomy table.
          </p>
        </div>
        <div className="page-hero__actions">
          <button className="btn btn--primary" onClick={() => setAddOpen(true)}>
            + Add Bill
          </button>
        </div>
      </div>

      <QuickAddBar
        onAdded={refetch}
        onOpenFullForm={() => setAddOpen(true)}
        showScheduleFields
      />

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
          onDuplicate={setDuplicateSource}
        />
      )}

      {(addOpen || editBill || duplicateSource) && (
        <BillFormModal
          bill={editBill ?? undefined}
          duplicateFrom={duplicateSource ?? undefined}
          onSave={handleSave}
          onClose={() => { setAddOpen(false); setEditBill(null); setDuplicateSource(null); }}
        />
      )}

      {deactivateTarget && (
        <ConfirmDialog
          title={`Deactivate "${deactivateTarget.name}"?`}
          message="It will be hidden from the schedule."
          confirmLabel={deactivating ? "Deactivating…" : "Deactivate"}
          confirmDisabled={deactivating}
          onConfirm={handleDeactivateConfirm}
          onCancel={() => setDeactivateTarget(null)}
        />
      )}
    </div>
  );
}
