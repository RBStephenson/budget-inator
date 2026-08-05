import { useState } from "react";
import { usePastPeriods } from "../hooks/usePastPeriods";
import { PeriodCard } from "./PeriodCard";

interface Props {
  currentStart: string;
  /** Refetches the current schedule — called alongside the past-window refetch so mutations here (mark paid, skip, move, etc.) also update the current period's balance. */
  onRefetch?: () => void;
}

/**
 * Collapsible "Past periods" section. Lets the user view completed pay periods
 * and retroactively mark a missed payment. Collapsed by default; the data is
 * only fetched once expanded.
 */
export function PastPeriods({ currentStart, onRefetch }: Props) {
  const [open, setOpen] = useState(false);
  const { data, status, refetch } = usePastPeriods(currentStart, open);

  function refetchAll() {
    refetch();
    onRefetch?.();
  }

  // Most recent first, so the immediately preceding period is at the top.
  const periods = data ? [...data.periods].reverse() : [];

  return (
    <section className="dashboard__past">
      <button
        className="dashboard__past-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="dashboard__past-chevron" aria-hidden>
          {open ? "▲" : "▼"}
        </span>
        Past periods
      </button>

      {open && (
        <div className="dashboard__past-body">
          {status === "loading" && (
            <p className="dashboard__state">Loading past periods…</p>
          )}
          {status === "error" && (
            <p className="dashboard__state dashboard__state--error">
              Could not load past periods.
            </p>
          )}
          {status === "ok" && periods.length === 0 && (
            <p className="dashboard__state">No past periods yet.</p>
          )}
          {status === "ok" &&
            periods.map((p) => (
              <PeriodCard
                key={p.period_index}
                period={p}
                label="Past"
                onRefetch={refetchAll}
              />
            ))}
        </div>
      )}
    </section>
  );
}
