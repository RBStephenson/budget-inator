import { useEffect, useState } from "react";
import { get } from "../api/client";
import type { ScheduleResponse } from "../types/schedule";

export type ScheduleStatus = "loading" | "error" | "empty" | "ok";

export function useSchedule() {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [status, setStatus] = useState<ScheduleStatus>("loading");

  useEffect(() => {
    get<ScheduleResponse>("/schedule")
      .then((d) => {
        setData(d);
        setStatus(d.periods.length === 0 ? "empty" : "ok");
      })
      .catch(() => setStatus("error"));
  }, []);

  return { data, status };
}
