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
  status: ScheduleStatus;
  refetch: () => void;
}

const ScheduleContext = createContext<ScheduleContextValue | null>(null);

export function ScheduleProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [status, setStatus] = useState<ScheduleStatus>("loading");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    get<ScheduleResponse>("/schedule")
      .then((d) => {
        if (!active) return;
        setData(d);
        setStatus(d.periods.length === 0 ? "empty" : "ok");
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setStatus("no-schedule");
        } else {
          setStatus("error");
        }
      });
    return () => {
      active = false;
    };
  }, [tick]);

  const refetch = useCallback(() => {
    setStatus("loading");
    setTick((t) => t + 1);
  }, []);

  return (
    <ScheduleContext.Provider value={{ data, status, refetch }}>
      {children}
    </ScheduleContext.Provider>
  );
}

export function useSchedule(): ScheduleContextValue {
  const ctx = useContext(ScheduleContext);
  if (!ctx) throw new Error("useSchedule must be used inside <ScheduleProvider>");
  return ctx;
}
