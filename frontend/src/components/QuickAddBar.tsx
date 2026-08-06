import { useState } from "react";
import { createBill } from "../api/bills";
import { useToast } from "../context/ToastContext";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  RECURRENCE_LABELS,
  type BillCategory,
  type BillCreate,
  type BillRecurrence,
} from "../types/bill";

interface Props {
  onAdded: () => void;
  onOpenFullForm: () => void;
  /** Show Recurrence + Due day/date fields (used on the Bills page). */
  showScheduleFields?: boolean;
}

function todayDayOfMonth(): number {
  return Math.min(new Date().getDate(), 28);
}

function todayIso(): string {
  return new Date().toLocaleDateString("en-CA");
}

export function QuickAddBar({ onAdded, onOpenFullForm, showScheduleFields = false }: Props) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<BillCategory>("other");
  const [recurrence, setRecurrence] = useState<BillRecurrence>("monthly");
  const [dueDay, setDueDay] = useState(String(todayDayOfMonth()));
  const [dueDate, setDueDate] = useState(todayIso());
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const isMonthly = recurrence === "monthly";
  const canSubmit =
    name.trim() !== "" &&
    amount.trim() !== "" &&
    !isNaN(parseFloat(amount)) &&
    parseFloat(amount) > 0 &&
    (!showScheduleFields || (isMonthly ? dueDay.trim() !== "" : dueDate.trim() !== ""));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || saving) return;
    setSaving(true);
    try {
      const payload: BillCreate = {
        name: name.trim(),
        amount: parseFloat(amount).toFixed(2),
        recurrence: showScheduleFields ? recurrence : "monthly",
        category,
      };
      if (showScheduleFields && isMonthly) {
        payload.due_day = parseInt(dueDay, 10);
      } else if (showScheduleFields) {
        payload.due_date = dueDate;
      } else {
        payload.due_day = todayDayOfMonth();
      }
      await createBill(payload);
      setName("");
      setAmount("");
      setCategory("other");
      setRecurrence("monthly");
      setDueDay(String(todayDayOfMonth()));
      setDueDate(todayIso());
      onAdded();
    } catch {
      addToast("Could not add the bill. Please try again.", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="quick-add" onSubmit={handleSubmit}>
      <input
        className="quick-add__input quick-add__input--name"
        type="text"
        placeholder="Bill name"
        aria-label="Bill name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <input
        className="quick-add__input quick-add__input--amount"
        type="number"
        min="0"
        step="0.01"
        placeholder="Amount"
        aria-label="Amount"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <select
        className="quick-add__input quick-add__input--category"
        aria-label="Category"
        value={category}
        onChange={(e) => setCategory(e.target.value as BillCategory)}
      >
        {CATEGORY_ORDER.map((c) => (
          <option key={c} value={c}>
            {CATEGORY_LABELS[c]}
          </option>
        ))}
      </select>
      {showScheduleFields && (
        <>
          <select
            className="quick-add__input quick-add__input--recurrence"
            aria-label="Recurrence"
            value={recurrence}
            onChange={(e) => setRecurrence(e.target.value as BillRecurrence)}
          >
            {Object.entries(RECURRENCE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {isMonthly ? (
            <input
              className="quick-add__input quick-add__input--due"
              type="number"
              min="1"
              max="31"
              placeholder="Due day"
              aria-label="Due day"
              value={dueDay}
              onChange={(e) => setDueDay(e.target.value)}
            />
          ) : (
            <input
              className="quick-add__input quick-add__input--due"
              type="date"
              aria-label="Next due date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          )}
        </>
      )}
      <button type="submit" className="btn btn--primary quick-add__submit" disabled={!canSubmit || saving}>
        {saving ? "Adding…" : "Add"}
      </button>
      <button type="button" className="quick-add__full-form" onClick={onOpenFullForm}>
        Open full form →
      </button>
    </form>
  );
}
