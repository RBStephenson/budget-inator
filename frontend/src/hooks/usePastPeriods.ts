import { useCallback, useEffect, useState } from "react";
import { get } from "../api/client";
import type { ScheduleResponse } from "../types/schedule";

export type PastPeriodsStatus = "idle" | "loading" | "error" | "ok";

// How far back to look for completed periods. ~32 days captures the
// immediately preceding period for every supported pay frequency (and a
// couple more for weekly/biweekly).
const PAST_WINDOW_DAYS = 32;

function isoDate(d: Date): string {
  return d.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

/**
 * Lazily fetches the pay periods immediately before `currentStart`.
 *
 * Only runs when `enabled` is true (the dashboard's "Past periods" section is
 * expanded), so the extra request is skipped on the common collapsed view.
 */
export function usePastPeriods(currentStart: string | null, enabled: boolean) {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled || !currentStart) return;
    let active = true;

    const to = new Date(currentStart + "T00:00:00");
    to.setDate(to.getDate() - 1); // day before the current period starts
    const from = new Date(to);
    from.setDate(from.getDate() - PAST_WINDOW_DAYS);

    get<ScheduleResponse>(`/schedule?from=${isoDate(from)}&to=${isoDate(to)}`)
      .then((d) => {
        if (!active) return;
        setData(d);
        setError(false);
      })
      .catch(() => {
        if (active) setError(true);
      });

    return () => {
      active = false;
    };
  }, [enabled, currentStart, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  let status: PastPeriodsStatus;
  if (!enabled) {
    status = "idle";
  } else if (error) {
    status = "error";
  } else if (data === null) {
    status = "loading";
  } else {
    status = "ok";
  }

  return { data, status, refetch };
}
