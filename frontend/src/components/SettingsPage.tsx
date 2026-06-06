import { useEffect, useRef, useState } from "react";
import { deleteAllData, exportData, importData } from "../api/data";
import {
  createPaySchedule,
  getPaySchedule,
  updatePaySchedule,
} from "../api/paySchedule";
import { ConfirmDialog } from "./ConfirmDialog";
import { Link } from "./Link";
import type { PayFrequency, PaySchedule } from "../types/paySchedule";
import { FREQUENCY_LABELS } from "../types/paySchedule";

type PageStatus = "loading" | "error" | "ready";
type SaveStatus = "idle" | "saving" | "saved" | "error";
type DataStatus = "idle" | "busy" | "done" | "error";

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

  const [exportStatus, setExportStatus] = useState<DataStatus>("idle");
  const [importStatus, setImportStatus] = useState<DataStatus>("idle");
  const [importError, setImportError] = useState<string | null>(null);
  const [deleteStatus, setDeleteStatus] = useState<DataStatus>("idle");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  async function handleExport() {
    setExportStatus("busy");
    try {
      const blob = await exportData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `budget-inator-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setExportStatus("done");
      setTimeout(() => setExportStatus("idle"), 3000);
    } catch {
      setExportStatus("error");
    }
  }

  async function handleImport(file: File) {
    setImportStatus("busy");
    setImportError(null);
    try {
      const text = await file.text();
      const payload = JSON.parse(text) as unknown;
      await importData(payload);
      setImportStatus("done");
      setTimeout(() => setImportStatus("idle"), 3000);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed");
      setImportStatus("error");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteConfirmed() {
    setShowDeleteConfirm(false);
    setDeleteStatus("busy");
    try {
      await deleteAllData();
      setDeleteStatus("done");
      setTimeout(() => setDeleteStatus("idle"), 3000);
    } catch {
      setDeleteStatus("error");
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
          <Link href="/" className="back-link">← Dashboard</Link>
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
      <div className="settings-section">
        <h3 className="settings-section__title">Data management</h3>

        <div className="settings-data__row">
          <div className="settings-data__item">
            <p className="settings-data__desc">
              Download a JSON backup of your pay schedule and bills.
            </p>
            <button
              className="btn btn--secondary"
              onClick={handleExport}
              disabled={exportStatus === "busy"}
              aria-label="Export backup"
            >
              {exportStatus === "busy" ? "Exporting…" : "Export backup"}
            </button>
            {exportStatus === "done" && (
              <span className="settings-data__ok">✓ Downloaded</span>
            )}
            {exportStatus === "error" && (
              <span className="settings-data__err">Export failed</span>
            )}
          </div>

          <div className="settings-data__item">
            <p className="settings-data__desc">
              Restore from a backup file. This overwrites all current data.
            </p>
            <label className="btn btn--secondary settings-data__file-label">
              {importStatus === "busy" ? "Importing…" : "Import backup"}
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                aria-label="Import backup file"
                className="settings-data__file-input"
                disabled={importStatus === "busy"}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleImport(file);
                }}
              />
            </label>
            {importStatus === "done" && (
              <span className="settings-data__ok">✓ Imported</span>
            )}
            {importStatus === "error" && (
              <span className="settings-data__err">{importError ?? "Import failed"}</span>
            )}
          </div>

          <div className="settings-data__item">
            <p className="settings-data__desc">
              Permanently delete all data and start over. This cannot be undone.
            </p>
            <button
              className="btn btn--danger"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteStatus === "busy"}
              aria-label="Delete all data"
            >
              {deleteStatus === "busy" ? "Deleting…" : "Delete all data"}
            </button>
            {deleteStatus === "done" && (
              <span className="settings-data__ok">✓ All data deleted</span>
            )}
            {deleteStatus === "error" && (
              <span className="settings-data__err">Delete failed</span>
            )}
          </div>
        </div>
      </div>

      {showDeleteConfirm && (
        <ConfirmDialog
          message="Delete all data? Your pay schedule, bills, and bill history will be permanently removed. This cannot be undone."
          confirmLabel="Delete everything"
          onConfirm={handleDeleteConfirmed}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  );
}
