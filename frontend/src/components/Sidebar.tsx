import { useSchedule } from "../context/ScheduleContext";
import { useDarkMode } from "../hooks/useDarkMode";
import { Link } from "./Link";

type Page = "dashboard" | "bills" | "settings" | "help" | "not-found";

interface Props {
  page: Page;
}

const NAV_ITEMS: { page: Page; href: string; icon: string; label: string }[] = [
  { page: "dashboard", href: "/", icon: "\u{1F3E0}", label: "Dashboard" },
  { page: "bills", href: "/bills", icon: "\u{1F9FE}", label: "Bills" },
  { page: "settings", href: "/settings", icon: "⚙️", label: "Settings" },
  { page: "help", href: "/help", icon: "❓", label: "Help" },
];

function formatPayDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function Sidebar({ page }: Props) {
  const { dark, toggle } = useDarkMode();
  const { data } = useSchedule();
  const nextPayDate = data?.periods?.[0]?.pay_date;
  const flaggedCount = data?.summary.total_flagged_bills ?? 0;

  return (
    <aside className="sidebar">
      <Link href="/" className="sidebar__logo">
        Budget-inator
      </Link>
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.page}
            href={item.href}
            className={
              item.page === page
                ? "sidebar__link sidebar__link--active"
                : "sidebar__link"
            }
            aria-current={item.page === page ? "page" : undefined}
          >
            <span aria-hidden="true">{item.icon}</span> {item.label}
            {item.page === "dashboard" && flaggedCount > 0 && (
              <span
                className="sidebar__nav-badge"
                aria-label={`${flaggedCount} bill${flaggedCount === 1 ? "" : "s"} cannot be paid on time`}
              >
                {flaggedCount}
              </span>
            )}
          </Link>
        ))}
      </nav>
      <div className="sidebar__footer">
        <button type="button" className="sidebar__theme-toggle" onClick={toggle}>
          {dark ? "☀ Light mode" : "\u{1F319} Dark mode"}
        </button>
        {nextPayDate && (
          <p className="sidebar__stat">
            <span className="sidebar__stat-label">Next payday</span>
            <span className="sidebar__stat-value">{formatPayDate(nextPayDate)}</span>
          </p>
        )}
      </div>
    </aside>
  );
}
