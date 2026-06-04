import { useSchedule } from "../hooks/useSchedule";
import { FlaggedBillsBanner } from "./FlaggedBillsBanner";
import { PeriodCard } from "./PeriodCard";

export function Dashboard() {
  const { data, status, refetch } = useSchedule();

  if (status === "loading") {
    return <p className="dashboard__state">Loading schedule…</p>;
  }

  if (status === "no-schedule") {
    return (
      <div className="dashboard__onboarding">
        <h2 className="dashboard__onboarding-title">Welcome to Budget-inator</h2>
        <p className="dashboard__onboarding-body">
          Set up your pay schedule to see your pay periods, assigned bills, and
          available-to-spend balance.
        </p>
        <a href="/settings" className="btn btn--primary">
          Set up pay schedule →
        </a>
      </div>
    );
  }

  if (status === "error") {
    return (
      <p className="dashboard__state dashboard__state--error">
        Could not load schedule. Make sure the API is running.
      </p>
    );
  }

  if (status === "empty" || !data || data.periods.length === 0) {
    return (
      <div className="dashboard__state">
        <p>No pay periods found. Set up your pay schedule to get started.</p>
      </div>
    );
  }

  const [current, ...upcoming] = data.periods;

  return (
    <div className="dashboard">
      {data.summary.total_flagged_bills > 0 && (
        <FlaggedBillsBanner periods={data.periods} />
      )}

      <PeriodCard period={current} isHero onRefetch={refetch} />

      {upcoming.length > 0 && (
        <section className="dashboard__upcoming">
          <h2 className="dashboard__upcoming-title">Upcoming periods</h2>
          {upcoming.map((p) => (
            <PeriodCard key={p.period_index} period={p} onRefetch={refetch} />
          ))}
        </section>
      )}

      <div className="dashboard__actions">
        <a href="/bills" className="btn btn--primary">
          + Add Bill
        </a>
      </div>
    </div>
  );
}
