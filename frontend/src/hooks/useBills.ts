import { useCallback, useEffect, useState } from "react";
import { listBills } from "../api/bills";
import type { Bill } from "../types/bill";

export type BillsStatus = "loading" | "error" | "ok";

export function useBills() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [status, setStatus] = useState<BillsStatus>("loading");

  const fetch = useCallback(() => {
    setStatus("loading");
    listBills()
      .then((data) => {
        setBills(data);
        setStatus("ok");
      })
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { bills, status, refetch: fetch };
}
