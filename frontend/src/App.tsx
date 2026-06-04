import { Dashboard } from "./components/Dashboard";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Budget-inator</h1>
      </header>
      <main>
        <Dashboard />
      </main>
    </div>
  );
}
