import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { fetchMonthlySummary } from "../api/monthlySchedule";
import type { MonthlySummaryResponse } from "../types/monthly";

export type MonthlyScheduleStatus = "idle" | "loading" | "error" | "no-schedule" | "ok";

export function useMonthlySchedule(enabled: boolean) {
  const [data, setData] = useState<MonthlySummaryResponse | null>(null);
  const [error, setError] = useState<"none" | "no-schedule" | "error">("none");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    fetchMonthlySummary()
      .then((d) => {
        if (!active) return;
        setData(d);
        setError("none");
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("no-schedule");
        } else {
          setError("error");
        }
      });
    return () => {
      active = false;
    };
  }, [enabled, tick]);

  const refetch = useCallback(() => {
    setData(null);
    setError("none");
    setTick((t) => t + 1);
  }, []);

  // Status is derived (not stored) so the loading transition on `enabled`
  // doesn't require a synchronous setState inside the effect.
  let status: MonthlyScheduleStatus;
  if (!enabled) {
    status = "idle";
  } else if (error === "no-schedule") {
    status = "no-schedule";
  } else if (error === "error") {
    status = "error";
  } else if (data === null) {
    status = "loading";
  } else {
    status = "ok";
  }

  return { data, status, refetch };
}
