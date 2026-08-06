import { useEffect, useState } from "react";
import { listPayPeriodActuals, putPayPeriodActual } from "../api/payPeriodActuals";
import { useToast } from "../context/ToastContext";
import type { PayPeriodActual } from "../types/payPeriodActual";
import type { PayPeriod } from "../types/schedule";

interface Props {
  period: PayPeriod;
  /** Called after actuals are saved, so the schedule can re-anchor. */
  onRecorded: () => void;
}

function fmtDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function todayISO(): string {
  return new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

/**
 * Persistent payday banner (#55). After a payday it asks the user to confirm
 * their actual deposit and balance, then re-anchors the rolling projection.
 * Stays until that period's actuals are recorded, then disappears. Keyed by
 * `original_pay_date` to match how the backend keys actuals.
 */
export function PaydayActualsBanner({ period, onRecorded }: Props) {
  const payDate = period.original_pay_date;
  const [actuals, setActuals] = useState<PayPeriodActual[] | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [netPay, setNetPay] = useState("");
  const [balance, setBalance] = useState("");
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    let active = true;
    listPayPeriodActuals()
      .then((d) => {
        if (active) setActuals(d);
      })
      .catch(() => {
        if (active) setActuals([]);
      });
    return () => {
      active = false;
    };
  }, []);

  // Don't render until we know the state (avoids a flash), once the payday has
  // passed, or once actuals for this payday are already recorded.
  if (actuals === null) return null;
  if (payDate > todayISO()) return null;
  const recorded = Array.isArray(actuals) && actuals.some((a) => a.pay_date === payDate);
  if (recorded) return null;

  function isValidAmount(raw: string): boolean {
    if (raw.trim() === "") return true;
    const parsed = parseFloat(raw);
    return !isNaN(parsed) && parsed >= 0;
  }

  const canSave =
    (netPay.trim() !== "" || balance.trim() !== "") &&
    isValidAmount(netPay) &&
    isValidAmount(balance);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (netPay.trim() === "" && balance.trim() === "") return;
    if (!isValidAmount(netPay) || !isValidAmount(balance)) {
      addToast("Enter a net pay and balance of 0 or more.", "error");
      return;
    }
    setSaving(true);
    try {
      await putPayPeriodActual(payDate, {
        actualNetPay: netPay.trim() || undefined,
        actualBalance: balance.trim() || undefined,
      });
      onRecorded();
      // Re-fetch so the banner dismisses itself.
      const fresh = await listPayPeriodActuals();
      setActuals(fresh);
    } catch {
      addToast("Could not save your payday actuals. Please try again.", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="payday-banner" role="region" aria-label="Confirm payday actuals">
      <div className="payday-banner__head">
        <span className="payday-banner__title">
          It is payday ({fmtDate(payDate)}) — confirm your deposit and balance
        </span>
        {!expanded && (
          <button
            className="btn btn--primary payday-banner__cta"
            onClick={() => setExpanded(true)}
          >
            Confirm
          </button>
        )}
      </div>

      {expanded && (
        <form className="payday-banner__form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="payday-net-pay">Actual net pay</label>
            <input
              id="payday-net-pay"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 2000.00"
              value={netPay}
              onChange={(e) => setNetPay(e.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="payday-balance">Current balance</label>
            <input
              id="payday-balance"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 3450.00"
              value={balance}
              onChange={(e) => setBalance(e.target.value)}
            />
          </div>
          <div className="payday-banner__actions">
            <button
              type="submit"
              className="btn btn--primary"
              disabled={saving || !canSave}
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setExpanded(false)}
              disabled={saving}
            >
              Not now
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
