import { useCallback, useEffect, useState } from "react";
import { ApiError, get } from "../api/client";
import type { ScheduleResponse } from "../types/schedule";

export type ScheduleStatus = "loading" | "error" | "no-schedule" | "empty" | "ok";

export function useSchedule() {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [status, setStatus] = useState<ScheduleStatus>("loading");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setStatus("loading");
    get<ScheduleResponse>("/schedule")
      .then((d) => {
        setData(d);
        setStatus(d.periods.length === 0 ? "empty" : "ok");
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setStatus("no-schedule");
        } else {
          setStatus("error");
        }
      });
  }, [tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { data, status, refetch };
}
