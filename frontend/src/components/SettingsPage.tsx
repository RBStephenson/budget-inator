import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import {
  deleteAllData,
  exportData,
  importData,
  previewImport,
  type ImportPreview,
} from "../api/data";
import {
  createPaySchedule,
  getPaySchedule,
  updatePaySchedule,
} from "../api/paySchedule";
import { saveBlob } from "../api/reports";
import { useSchedule } from "../context/ScheduleContext";
import { useToast } from "../context/ToastContext";
import { navigate } from "../router";
import { ConfirmDialog } from "./ConfirmDialog";
import { Link } from "./Link";
import type { PayFrequency, PaySchedule } from "../types/paySchedule";
import { FREQUENCY_LABELS } from "../types/paySchedule";

type PageStatus = "loading" | "error" | "ready";
type SaveStatus = "idle" | "saving" | "saved" | "error";
type DataStatus = "idle" | "busy" | "done" | "error";

function fmtDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface PendingImport {
  file: File;
  payload: unknown;
  summary: ImportPreview;
}

interface RejectedImport {
  file: File;
  errors: string[];
}

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
  const [deleteStatus, setDeleteStatus] = useState<DataStatus>("idle");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [previewStatus, setPreviewStatus] = useState<DataStatus>("idle");
  const [pendingImport, setPendingImport] = useState<PendingImport | null>(null);
  const [rejectedImport, setRejectedImport] = useState<RejectedImport | null>(null);
  const { addToast } = useToast();
  const { refetch: refetchSchedule } = useSchedule();
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
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 3000);
        refetchSchedule();
      } else {
        // First-time setup: create, then go to the dashboard (the button is
        // labelled "Save and go to dashboard"). Don't touch state afterward —
        // navigation unmounts this page.
        await createPaySchedule(payload);
        refetchSchedule();
        navigate("/");
      }
    } catch {
      setSaveStatus("error");
    }
  }

  async function handleExport() {
    setExportStatus("busy");
    try {
      const blob = await exportData();
      saveBlob(blob, `budget-inator-backup-${new Date().toISOString().slice(0, 10)}.json`);
      setExportStatus("done");
      setTimeout(() => setExportStatus("idle"), 3000);
    } catch {
      setExportStatus("idle");
      addToast("Export failed. Please try again.", "error");
    }
  }

  async function handleFileSelected(file: File) {
    setPreviewStatus("busy");
    try {
      const text = await file.text();
      const payload = JSON.parse(text) as unknown;
      const summary = await previewImport(payload);
      setPendingImport({ file, payload, summary });
      setPreviewStatus("idle");
    } catch (err) {
      setPreviewStatus("idle");
      if (err instanceof ApiError && err.fieldErrors.length > 0) {
        setRejectedImport({ file, errors: err.fieldErrors });
      } else {
        addToast(
          err instanceof Error ? err.message : "Could not read that file.",
          "error",
        );
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    }
  }

  function handleImportCancelled() {
    setPendingImport(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleRejectedImportClosed() {
    setRejectedImport(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleImportConfirmed() {
    if (!pendingImport) return;
    const { payload } = pendingImport;
    setPendingImport(null);
    setImportStatus("busy");
    try {
      await importData(payload);
      // Import replaces all data, so the loaded schedule/form is now stale —
      // re-sync from the server before the user can save over it.
      try {
        const sched = await getPaySchedule();
        setExisting(sched);
        setForm(initialForm(sched));
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 404) throw err;
        setExisting(null);
        setForm(initialForm(null));
      }
      setErrors({});
      setImportStatus("done");
      setTimeout(() => setImportStatus("idle"), 3000);
      refetchSchedule();
    } catch (err) {
      setImportStatus("idle");
      addToast(err instanceof Error ? err.message : "Import failed.", "error");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteConfirmed() {
    setShowDeleteConfirm(false);
    setDeleteStatus("busy");
    try {
      await deleteAllData();
      // The schedule row is gone — reset to the create form so the next save
      // POSTs a new schedule instead of PATCHing a deleted row (which 404s).
      setExisting(null);
      setForm(initialForm(null));
      setErrors({});
      setSaveStatus("idle");
      setDeleteStatus("done");
      setTimeout(() => setDeleteStatus("idle"), 3000);
      refetchSchedule();
    } catch {
      setDeleteStatus("idle");
      addToast("Delete failed. Please try again.", "error");
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
      <div className="page-hero page-hero--settings">
        <div className="page-hero__copy">
          <Link href="/" className="back-link">← Dashboard</Link>
          <p className="page-hero__eyebrow">Settings</p>
          <h2 className="page-hero__title">Tune the budget engine</h2>
          <p className="page-hero__subtitle">
            Keep your paycheck rhythm, starting balance, and backup tools aligned with real life.
          </p>
        </div>
        <div className="page-hero__meta">
          <span className="page-hero__pill">
            {isNew ? "First-time setup" : "Pay schedule active"}
          </span>
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

      <div className="settings-page__content">
        <form onSubmit={handleSubmit} noValidate className="settings-form settings-card">
          <div className="settings-card__header">
            <p className="settings-card__eyebrow">Pay schedule</p>
            <h3 className="settings-card__title">Income cadence</h3>
          </div>
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
              {form.frequency === "semimonthly" && (
                <span className="form-hint">
                  Use a 1st/15th anchor for that pattern, or a paycheck after the
                  15th for a 15th/month-end schedule.
                </span>
              )}
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

        <div className="settings-section settings-card">
          <div className="settings-card__header">
            <p className="settings-card__eyebrow">Data management</p>
            <h3 className="settings-card__title">Backups and reset</h3>
          </div>

          <div className="settings-data__row">
            <div className="settings-data__item">
              <p className="settings-data__desc">
                Download a JSON backup of your pay schedule, bills, and
                payment history.
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
            </div>

            <div className="settings-data__item">
              <p className="settings-data__desc">
                Restore from a backup file. This overwrites all current data.
              </p>
              <label className="btn btn--secondary settings-data__file-label">
                {previewStatus === "busy"
                  ? "Checking file…"
                  : importStatus === "busy"
                    ? "Importing…"
                    : "Import backup"}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,application/json"
                  aria-label="Import backup file"
                  className="settings-data__file-input"
                  disabled={previewStatus === "busy" || importStatus === "busy"}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void handleFileSelected(file);
                  }}
                />
              </label>
              {importStatus === "done" && (
                <span className="settings-data__ok">✓ Imported</span>
              )}
            </div>

            <div className="settings-data__item settings-data__item--danger">
              <p className="settings-data__desc">
                Permanently delete all data and start over. This cannot be undone.
              </p>
              <button
                className="btn btn--danger"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleteStatus === "busy"}
                aria-label="Delete all data"
              >
                <span aria-hidden="true">🗑 </span>
                {deleteStatus === "busy" ? "Deleting…" : "Delete all data"}
              </button>
              {deleteStatus === "done" && (
                <span className="settings-data__ok">✓ All data deleted</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {pendingImport && (
        <ConfirmDialog
          title="Import backup?"
          message={`This overwrites all current data with the contents of "${pendingImport.file.name}".`}
          confirmLabel="Import and overwrite"
          onConfirm={handleImportConfirmed}
          onCancel={handleImportCancelled}
        >
          <dl className="import-preview">
            {pendingImport.summary.pay_schedule && (
              <>
                <dt>Pay schedule</dt>
                <dd>
                  {FREQUENCY_LABELS[
                    pendingImport.summary.pay_schedule.frequency as PayFrequency
                  ] ?? pendingImport.summary.pay_schedule.frequency}
                  , ${pendingImport.summary.pay_schedule.net_salary} net,
                  first paycheck {fmtDate(pendingImport.summary.pay_schedule.first_paycheck_date)}
                </dd>
              </>
            )}
            <dt>Bills</dt>
            <dd>{pendingImport.summary.bill_count}</dd>
            <dt>Payment history entries</dt>
            <dd>{pendingImport.summary.bill_instance_count}</dd>
          </dl>
        </ConfirmDialog>
      )}

      {rejectedImport && (
        <ConfirmDialog
          title="This backup file can't be imported"
          message={`"${rejectedImport.file.name}" failed validation. Nothing was changed.`}
          cancelLabel="Close"
          hideConfirm
          onConfirm={handleRejectedImportClosed}
          onCancel={handleRejectedImportClosed}
        >
          <ul className="import-preview__errors">
            {rejectedImport.errors.map((msg) => (
              <li key={msg}>{msg}</li>
            ))}
          </ul>
        </ConfirmDialog>
      )}

      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete all data?"
          message="Your pay schedule, bills, and bill history will be permanently removed. This cannot be undone."
          confirmLabel="Delete everything"
          onConfirm={handleDeleteConfirmed}
          onCancel={() => setShowDeleteConfirm(false)}
          destructive
        />
      )}
    </div>
  );
}
