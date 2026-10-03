import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError, get } from "../api/client";
import type { ScheduleResponse } from "../types/schedule";

export type ScheduleStatus = "loading" | "error" | "no-schedule" | "empty" | "ok";

interface ScheduleContextValue {
  data: ScheduleResponse | null;
  /** "loading" only before the first response; refetches keep the last status. */
  status: ScheduleStatus;
  /** True while a refetch is in flight; the previous data stays available. */
  refreshing: boolean;
  refetch: () => void;
}

const ScheduleContext = createContext<ScheduleContextValue | null>(null);

export function ScheduleProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [status, setStatus] = useState<ScheduleStatus>("loading");
  const [refreshing, setRefreshing] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    get<ScheduleResponse>("/schedule")
      .then((d) => {
        if (!active) return;
        setData(d);
        setStatus(d.periods.length === 0 ? "empty" : "ok");
        setRefreshing(false);
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setStatus("no-schedule");
        } else {
          setStatus("error");
        }
        setRefreshing(false);
      });
    return () => {
      active = false;
    };
  }, [tick]);

  // Keep the current data and status while refetching (BI-65). Resetting
  // status to "loading" here made the Dashboard swap its whole tree for a
  // loading message and remount it, discarding every expanded card and the
  // open Past periods section on each bill action.
  const refetch = useCallback(() => {
    setRefreshing(true);
    setTick((t) => t + 1);
  }, []);

  return (
    <ScheduleContext.Provider value={{ data, status, refreshing, refetch }}>
      {children}
    </ScheduleContext.Provider>
  );
}

export function useSchedule(): ScheduleContextValue {
  const ctx = useContext(ScheduleContext);
  if (!ctx) throw new Error("useSchedule must be used inside <ScheduleProvider>");
  return ctx;
}
