import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "budgetinator-dark";

function readStored(): boolean {
  return localStorage.getItem(STORAGE_KEY) === "1";
}

export function useDarkMode() {
  const [dark, setDark] = useState(readStored);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem(STORAGE_KEY, dark ? "1" : "0");
  }, [dark]);

  const toggle = useCallback(() => setDark((d) => !d), []);

  return { dark, toggle };
}
