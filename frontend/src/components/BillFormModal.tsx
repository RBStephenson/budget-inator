import { useEffect, useRef, useState } from "react";
import { createBill, updateBill } from "../api/bills";
import { useToast } from "../context/ToastContext";
import type { Bill, BillCategory, BillRecurrence } from "../types/bill";
import { CATEGORY_LABELS, RECURRENCE_LABELS } from "../types/bill";

interface Props {
  bill?: Bill;
  onSave: () => void;
  onClose: () => void;
}

interface FormState {
  effective_date: string;
  name: string;
  amount: string;
  recurrence: BillRecurrence;
  due_day: string;
  due_day_is_month_end: boolean;
  due_date: string;
  grace_period_days: string;
  category: BillCategory | "";
  is_variable: boolean;
  sinking_fund_enabled: boolean;
  notes: string;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function initialState(bill?: Bill): FormState {
  return {
    effective_date: bill ? todayIso() : "",
    name: bill?.name ?? "",
    amount: bill ? String(parseFloat(bill.amount)) : "",
    recurrence: bill?.recurrence ?? "monthly",
    due_day: bill?.due_day != null ? String(bill.due_day) : "",
    due_day_is_month_end: bill?.due_day_is_month_end ?? false,
    due_date: bill?.due_date ?? "",
    grace_period_days: bill ? String(bill.grace_period_days) : "",
    category: bill?.category ?? "",
    is_variable: bill?.is_variable ?? false,
    sinking_fund_enabled: bill?.sinking_fund_enabled ?? false,
    notes: bill?.notes ?? "",
  };
}

const RECURRENCES = Object.keys(RECURRENCE_LABELS) as BillRecurrence[];
const CATEGORIES = Object.keys(CATEGORY_LABELS) as BillCategory[];

export function BillFormModal({ bill, onSave, onClose }: Props) {
  const [form, setForm] = useState<FormState>(() => initialState(bill));
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  // When recurrence changes, clear the field that no longer applies
  function setRecurrence(r: BillRecurrence) {
    setForm((f) => ({
      ...f,
      recurrence: r,
      due_day: r === "monthly" ? f.due_day : "",
      due_day_is_month_end: r === "monthly" ? f.due_day_is_month_end : false,
      due_date: r !== "monthly" ? f.due_date : "",
    }));
  }

  function validate(): boolean {
    const e: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) e.name = "Name is required.";
    const amt = parseFloat(form.amount);
    if (!form.amount || isNaN(amt) || amt <= 0) e.amount = "Enter a positive amount.";
    if (!form.category) e.category = "Category is required.";
    if (form.recurrence === "monthly") {
      const d = parseInt(form.due_day);
      if (
        !form.due_day_is_month_end &&
        (!form.due_day || isNaN(d) || d < 1 || d > 31)
      )
        e.due_day = "Enter a day between 1 and 31.";
    } else {
      if (!form.due_date) e.due_date = "Due date is required.";
    }
    const grace = form.grace_period_days;
    if (grace !== "" && (isNaN(parseInt(grace)) || parseInt(grace) < 0))
      e.grace_period_days = "Enter 0 or a positive number of days.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        ...(bill ? { effective_date: form.effective_date || todayIso() } : {}),
        name: form.name.trim(),
        amount: form.amount,
        recurrence: form.recurrence,
        ...(form.recurrence === "monthly"
          ? {
              due_day: form.due_day_is_month_end ? null : parseInt(form.due_day),
              due_day_is_month_end: form.due_day_is_month_end,
            }
          : { due_date: form.due_date }),
        grace_period_days: form.grace_period_days ? parseInt(form.grace_period_days) : 0,
        category: form.category as BillCategory,
        is_variable: form.is_variable,
        sinking_fund_enabled: form.sinking_fund_enabled,
        notes: form.notes.trim() || null,
        // Restore active when saving an inactive bill via edit
        ...(bill && !bill.is_active ? { is_active: true } : {}),
      };
      if (bill) {
        await updateBill(bill.id, payload);
      } else {
        await createBill(payload);
      }
      onSave();
    } catch {
      addToast("Failed to save bill. Please try again.", "error");
    } finally {
      setSubmitting(false);
    }
  }

  const isMonthly = form.recurrence === "monthly";

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label={bill ? "Edit bill" : "Add bill"}>
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title">{bill ? "Edit bill" : "Add bill"}</h2>
          <button className="modal__close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-grid">
            <div className="form-field form-field--wide">
              <label htmlFor="bf-name">Name</label>
              <input
                id="bf-name"
                ref={nameRef}
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
              {errors.name && <span className="form-error">{errors.name}</span>}
            </div>

            {bill && (
              <div className="form-field">
                <label htmlFor="bf-effective-date">Effective date</label>
                <input
                  id="bf-effective-date"
                  type="date"
                  value={form.effective_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, effective_date: e.target.value }))
                  }
                />
                <span className="form-hint">
                  Applies this edit from this date forward. Use payment status to
                  correct one occurrence.
                </span>
              </div>
            )}

            <div className="form-field">
              <label htmlFor="bf-amount">
                Amount {form.is_variable && <span className="form-hint">(estimated)</span>}
              </label>
              <input
                id="bf-amount"
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              />
              {errors.amount && <span className="form-error">{errors.amount}</span>}
            </div>

            <div className="form-field">
              <label htmlFor="bf-category">Category</label>
              <select
                id="bf-category"
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value as BillCategory }))}
              >
                <option value="">Select…</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
              {errors.category && <span className="form-error">{errors.category}</span>}
            </div>

            <div className="form-field">
              <label htmlFor="bf-recurrence">Recurrence</label>
              <select
                id="bf-recurrence"
                value={form.recurrence}
                onChange={(e) => setRecurrence(e.target.value as BillRecurrence)}
              >
                {RECURRENCES.map((r) => (
                  <option key={r} value={r}>{RECURRENCE_LABELS[r]}</option>
                ))}
              </select>
            </div>

            {isMonthly ? (
              <div className="form-field">
                <label htmlFor="bf-due-day">Due day (1–31)</label>
                <input
                  id="bf-due-day"
                  type="number"
                  min="1"
                  max="31"
                  value={form.due_day}
                  disabled={form.due_day_is_month_end}
                  onChange={(e) => setForm((f) => ({ ...f, due_day: e.target.value }))}
                />
                <label className="form-toggle">
                  <input
                    type="checkbox"
                    checked={form.due_day_is_month_end}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        due_day_is_month_end: e.target.checked,
                      }))
                    }
                  />
                  Last day of month
                </label>
                {errors.due_day && <span className="form-error">{errors.due_day}</span>}
              </div>
            ) : (
              <div className="form-field">
                <label htmlFor="bf-due-date">Due date</label>
                <input
                  id="bf-due-date"
                  type="date"
                  value={form.due_date}
                  onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                />
                {errors.due_date && <span className="form-error">{errors.due_date}</span>}
              </div>
            )}

            <div className="form-field">
              <label htmlFor="bf-grace">Grace period (days)</label>
              <input
                id="bf-grace"
                type="number"
                min="0"
                placeholder="0"
                value={form.grace_period_days}
                onChange={(e) => setForm((f) => ({ ...f, grace_period_days: e.target.value }))}
              />
              {errors.grace_period_days && (
                <span className="form-error">{errors.grace_period_days}</span>
              )}
            </div>

            <div className="form-field form-field--wide">
              <label className="form-toggle">
                <input
                  type="checkbox"
                  checked={form.is_variable}
                  onChange={(e) => setForm((f) => ({ ...f, is_variable: e.target.checked }))}
                />
                Variable amount (actual may differ from estimate)
              </label>
            </div>

            <div className="form-field form-field--wide">
              <label className="form-toggle">
                <input
                  type="checkbox"
                  checked={form.sinking_fund_enabled}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      sinking_fund_enabled: e.target.checked,
                    }))
                  }
                />
                Build a sinking fund for this bill
              </label>
              <span className="form-hint">
                Reserves part of each paycheck before the next due date, useful
                for quarterly, semi-annual, and annual bills.
              </span>
            </div>

            <div className="form-field form-field--wide">
              <label htmlFor="bf-notes">Notes (optional)</label>
              <textarea
                id="bf-notes"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              />
            </div>
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={submitting}>
              {submitting ? "Saving…" : bill ? "Save changes" : "Add bill"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
