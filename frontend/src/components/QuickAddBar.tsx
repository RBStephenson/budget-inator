import { useState } from "react";
import { createBill } from "../api/bills";
import { useToast } from "../context/ToastContext";
import { CATEGORY_LABELS, CATEGORY_ORDER, type BillCategory } from "../types/bill";

interface Props {
  onAdded: () => void;
  onOpenFullForm: () => void;
}

function todayDayOfMonth(): number {
  return Math.min(new Date().getDate(), 28);
}

export function QuickAddBar({ onAdded, onOpenFullForm }: Props) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<BillCategory>("other");
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const canSubmit = name.trim() !== "" && amount.trim() !== "" && !isNaN(parseFloat(amount));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || saving) return;
    setSaving(true);
    try {
      await createBill({
        name: name.trim(),
        amount: parseFloat(amount).toFixed(2),
        recurrence: "monthly",
        due_day: todayDayOfMonth(),
        category,
      });
      setName("");
      setAmount("");
      setCategory("other");
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
      <button type="submit" className="btn btn--primary quick-add__submit" disabled={!canSubmit || saving}>
        {saving ? "Adding…" : "Add"}
      </button>
      <button type="button" className="quick-add__full-form" onClick={onOpenFullForm}>
        Open full form →
      </button>
    </form>
  );
}
