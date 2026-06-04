import { useEffect, useState } from "react";
import { get } from "./api/client";

type ApiStatus = "loading" | "ok" | "error";

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("loading");

  useEffect(() => {
    get<{ status: string }>("/health")
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("error"));
  }, []);

  const statusLabel: Record<ApiStatus, string> = {
    loading: "Connecting…",
    ok: "API connected",
    error: "API unreachable",
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Budget-inator</h1>
        <span className={`api-status ${apiStatus}`}>
          {statusLabel[apiStatus]}
        </span>
      </header>
      <main>
        <p>Your pay-period budget planner. Coming soon.</p>
      </main>
    </div>
  );
}
