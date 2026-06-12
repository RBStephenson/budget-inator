import { useCallback, useEffect, useState } from "react";
import { listBills } from "../api/bills";
import type { Bill } from "../types/bill";

export type BillsStatus = "loading" | "error" | "ok";

export function useBills() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [status, setStatus] = useState<BillsStatus>("loading");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    listBills()
      .then((data) => {
        if (!active) return;
        setBills(data);
        setStatus("ok");
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [tick]);

  const refetch = useCallback(() => {
    setStatus("loading");
    setTick((t) => t + 1);
  }, []);

  return { bills, status, refetch };
}
