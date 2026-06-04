import { useEffect, useState } from "react";
import {
  createPaySchedule,
  getPaySchedule,
  updatePaySchedule,
} from "../api/paySchedule";
import type { PayFrequency, PaySchedule } from "../types/paySchedule";
import { FREQUENCY_LABELS } from "../types/paySchedule";

type PageStatus = "loading" | "error" | "ready";
type SaveStatus = "idle" | "saving" | "saved" | "error";

interface FormState {
  net_salary: string;
  first_paycheck_date: string;
  beginning_balance: string;
  frequency: PayFrequency;
}

function initialForm(existing: PaySchedule | null): FormState {
  return {
    net_salary: existing ? String(parseFloat(existing.net_salary)) : "",
    first_paycheck_date: existing?.first_paycheck_date ?? "",
    beginning_balance: existing ? String(parseFloat(existing.beginning_balance)) : "",
    frequency: existing?.frequency ?? "biweekly",
  };
}

const FREQUENCIES = Object.keys(FREQUENCY_LABELS) as PayFrequency[];

export function SettingsPage() {
  const [pageStatus, setPageStatus] = useState<PageStatus>("loading");
  const [existing, setExisting] = useState<PaySchedule | null>(null);
  const [form, setForm] = useState<FormState>(initialForm(null));
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");

  useEffect(() => {
    getPaySchedule()
      .then((sched) => {
        setExisting(sched);
        setForm(initialForm(sched));
        setPageStatus("ready");
      })
      .catch(() => setPageStatus("error"));
  }, []);

  function validate(): boolean {
    const e: Partial<Record<keyof FormState, string>> = {};
    const salary = parseFloat(form.net_salary);
    if (!form.net_salary || isNaN(salary) || salary <= 0)
      e.net_salary = "Enter a salary greater than $0.";
    const balance = parseFloat(form.beginning_balance);
    if (form.beginning_balance === "" || isNaN(balance) || balance < 0)
      e.beginning_balance = "Enter your current balance (0 or more).";
    if (!form.first_paycheck_date)
      e.first_paycheck_date = "Select the date of your next (or most recent) paycheck.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setSaveStatus("saving");
    try {
      const payload = {
        net_salary: form.net_salary,
        first_paycheck_date: form.first_paycheck_date,
        beginning_balance: form.beginning_balance,
        frequency: form.frequency,
      };
      if (existing) {
        const updated = await updatePaySchedule(payload);
        setExisting(updated);
      } else {
        const created = await createPaySchedule(payload);
        setExisting(created);
      }
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    }
  }

  if (pageStatus === "loading") {
    return <p className="dashboard__state">Loading settings…</p>;
  }

  if (pageStatus === "error") {
    return (
      <p className="dashboard__state dashboard__state--error">
        Could not load settings. Make sure the API is running.
      </p>
    );
  }

  const isNew = existing === null;

  return (
    <div className="settings-page">
      <div className="settings-page__header">
        <div>
          <a href="/" className="back-link">← Dashboard</a>
          <h2 className="settings-page__title">Pay schedule</h2>
        </div>
      </div>

      {isNew && (
        <div className="settings-page__intro">
          <p>
            Enter your pay details below. Budget-inator will use these to generate
            your pay periods and assign bills automatically.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="settings-form">
        <div className="settings-form__grid">
          <div className="form-field">
            <label htmlFor="ps-salary">Net salary (per paycheck)</label>
            <input
              id="ps-salary"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 2000.00"
              value={form.net_salary}
              onChange={(e) => setForm((f) => ({ ...f, net_salary: e.target.value }))}
            />
            {errors.net_salary && (
              <span className="form-error">{errors.net_salary}</span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="ps-frequency">Pay frequency</label>
            <select
              id="ps-frequency"
              value={form.frequency}
              onChange={(e) =>
                setForm((f) => ({ ...f, frequency: e.target.value as PayFrequency }))
              }
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {FREQUENCY_LABELS[f]}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="ps-start-date">
              First paycheck date
              <span className="form-hint"> — anchor date for computing periods</span>
            </label>
            <input
              id="ps-start-date"
              type="date"
              value={form.first_paycheck_date}
              onChange={(e) =>
                setForm((f) => ({ ...f, first_paycheck_date: e.target.value }))
              }
            />
            {errors.first_paycheck_date && (
              <span className="form-error">{errors.first_paycheck_date}</span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="ps-balance">
              Current balance
              <span className="form-hint"> — what's in your account right now</span>
            </label>
            <input
              id="ps-balance"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 500.00"
              value={form.beginning_balance}
              onChange={(e) =>
                setForm((f) => ({ ...f, beginning_balance: e.target.value }))
              }
            />
            {errors.beginning_balance && (
              <span className="form-error">{errors.beginning_balance}</span>
            )}
          </div>
        </div>

        <div className="settings-form__footer">
          <button
            type="submit"
            className="btn btn--primary"
            disabled={saveStatus === "saving"}
          >
            {saveStatus === "saving"
              ? "Saving…"
              : isNew
                ? "Save and go to dashboard"
                : "Save changes"}
          </button>

          {saveStatus === "saved" && (
            <span className="settings-form__saved">✓ Saved</span>
          )}
          {saveStatus === "error" && (
            <span className="settings-form__save-error">Failed to save. Try again.</span>
          )}
        </div>
      </form>
    </div>
  );
}
