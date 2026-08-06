import { useEffect, useState } from "react";
import { BillsPage } from "./components/BillsPage";
import { Dashboard } from "./components/Dashboard";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HelpPage } from "./components/HelpPage";
import { NotFound } from "./components/NotFound";
import { SettingsPage } from "./components/SettingsPage";
import { Sidebar } from "./components/Sidebar";
import { ToastContainer } from "./components/ToastContainer";
import { ScheduleProvider } from "./context/ScheduleContext";
import { ToastProvider } from "./context/ToastContext";
import "./App.css";

type Page = "dashboard" | "bills" | "settings" | "help" | "not-found";

function getPage(): Page {
  const path = window.location.pathname;
  if (path === "/" || path === "") return "dashboard";
  if (path.startsWith("/bills")) return "bills";
  if (path.startsWith("/settings")) return "settings";
  if (path.startsWith("/help")) return "help";
  return "not-found";
}

export default function App() {
  const [page, setPage] = useState(getPage);

  useEffect(() => {
    const handler = () => setPage(getPage());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  return (
    <ErrorBoundary>
      <ToastProvider>
      <ScheduleProvider>
      <div className="app-shell">
        <Sidebar page={page} />
        <div className="app">
          <main>
            {page === "bills" ? (
              <BillsPage />
            ) : page === "settings" ? (
              <SettingsPage />
            ) : page === "help" ? (
              <HelpPage />
            ) : page === "not-found" ? (
              <NotFound />
            ) : (
              <Dashboard />
            )}
          </main>
          <ToastContainer />
        </div>
      </div>
      </ScheduleProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
