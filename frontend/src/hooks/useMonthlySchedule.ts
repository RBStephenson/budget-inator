import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { fetchMonthlySummary } from "../api/monthlySchedule";
import type { MonthlySummaryResponse } from "../types/monthly";

export type MonthlyScheduleStatus = "idle" | "loading" | "error" | "no-schedule" | "ok";

export function useMonthlySchedule(enabled: boolean) {
  const [data, setData] = useState<MonthlySummaryResponse | null>(null);
  const [status, setStatus] = useState<MonthlyScheduleStatus>("idle");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    setStatus("loading");
    fetchMonthlySummary()
      .then((d) => {
        setData(d);
        setStatus("ok");
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setStatus("no-schedule");
        } else {
          setStatus("error");
        }
      });
  }, [enabled, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { data, status, refetch };
}
