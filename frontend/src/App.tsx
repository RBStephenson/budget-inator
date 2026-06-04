import { useEffect, useState } from "react";
import { BillsPage } from "./components/BillsPage";
import { Dashboard } from "./components/Dashboard";
import { SettingsPage } from "./components/SettingsPage";
import "./App.css";

type Page = "dashboard" | "bills" | "settings";

function getPage(): Page {
  const path = window.location.pathname;
  if (path.startsWith("/bills")) return "bills";
  if (path.startsWith("/settings")) return "settings";
  return "dashboard";
}

export default function App() {
  const [page, setPage] = useState(getPage);

  useEffect(() => {
    const handler = () => setPage(getPage());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Budget-inator</h1>
      </header>
      <main>
        {page === "bills" ? (
          <BillsPage />
        ) : page === "settings" ? (
          <SettingsPage />
        ) : (
          <Dashboard />
        )}
      </main>
    </div>
  );
}
