import { useEffect, useState } from "react";
import { BillsPage } from "./components/BillsPage";
import { Dashboard } from "./components/Dashboard";
import "./App.css";

function getPage(): "dashboard" | "bills" {
  return window.location.pathname.startsWith("/bills") ? "bills" : "dashboard";
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
        {page === "bills" ? <BillsPage /> : <Dashboard />}
      </main>
    </div>
  );
}
