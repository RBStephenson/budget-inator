import { useState } from "react";
import { useSchedule } from "../hooks/useSchedule";
import { useMonthlySchedule } from "../hooks/useMonthlySchedule";
import { downloadBudgetPdf } from "../api/reports";
import { useToast } from "../context/ToastContext";
import { AnnualCostModal } from "./AnnualCostModal";
import { FlaggedBillsBanner } from "./FlaggedBillsBanner";
import { Link } from "./Link";
import { MonthCard } from "./MonthCard";
import { PastPeriods } from "./PastPeriods";
import { PaydayActualsBanner } from "./PaydayActualsBanner";
import { PeriodCard } from "./PeriodCard";

type DashboardView = "periods" | "monthly";

export function Dashboard() {
  const [view, setView] = useState<DashboardView>("periods");
  const [downloading, setDownloading] = useState(false);
  const [showAnnualCost, setShowAnnualCost] = useState(false);
  const { addToast } = useToast();
  const { data, status, refetch } = useSchedule();
  const {
    data: monthlyData,
    status: monthlyStatus,
  } = useMonthlySchedule(view === "monthly");

  async function handleDownloadPdf() {
    setDownloading(true);
    try {
      await downloadBudgetPdf();
    } catch {
      addToast("Could not generate the PDF. Please try again.", "error");
    } finally {
      setDownloading(false);
    }
  }

  const isLoading =
    view === "periods" ? status === "loading" : monthlyStatus === "loading" || monthlyStatus === "idle";
  const isError =
    view === "periods" ? status === "error" : monthlyStatus === "error";
  const noSchedule =
    view === "periods"
      ? status === "no-schedule"
      : monthlyStatus === "no-schedule";

  if (isLoading) {
    return <p className="dashboard__state">Loading schedule…</p>;
  }

  if (noSchedule) {
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

  if (isError) {
    return (
      <p className="dashboard__state dashboard__state--error">
        Could not load schedule. Make sure the API is running.
      </p>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard__view-toggle" role="group" aria-label="Dashboard view">
        <button
          className={`btn-view-toggle${view === "periods" ? " btn-view-toggle--active" : ""}`}
          onClick={() => setView("periods")}
          aria-pressed={view === "periods"}
        >
          By Pay Period
        </button>
        <button
          className={`btn-view-toggle${view === "monthly" ? " btn-view-toggle--active" : ""}`}
          onClick={() => setView("monthly")}
          aria-pressed={view === "monthly"}
        >
          By Month
        </button>
      </div>

      <div className="dashboard__actions">
        <Link href="/bills" className="btn btn--primary">
          + Add Bill
        </Link>
        <button
          className="btn btn--secondary"
          onClick={() => setShowAnnualCost(true)}
        >
          Annual Cost
        </button>
        <button
          className="btn btn--secondary"
          onClick={handleDownloadPdf}
          disabled={downloading}
        >
          {downloading ? "Generating PDF…" : "Download PDF"}
        </button>
      </div>

      {view === "periods" && data && data.periods.length > 0 && (
        <>
          {data.summary.total_flagged_bills > 0 && (
            <FlaggedBillsBanner periods={data.periods} />
          )}
          {(() => {
            const [current, ...upcoming] = data.periods;
            return (
              <>
                <PaydayActualsBanner period={current} onRecorded={refetch} />
                <PeriodCard period={current} isHero onRefetch={refetch} />
                {upcoming.length > 0 && (
                  <section className="dashboard__upcoming">
                    <h2 className="dashboard__upcoming-title">Upcoming periods</h2>
                    {upcoming.map((p) => (
                      <PeriodCard key={p.period_index} period={p} onRefetch={refetch} />
                    ))}
                  </section>
                )}
                <PastPeriods currentStart={current.period_start} />
              </>
            );
          })()}
        </>
      )}

      {view === "periods" && (!data || data.periods.length === 0) && (
        <div className="dashboard__state">
          <p>No pay periods found. Set up your pay schedule to get started.</p>
        </div>
      )}

      {view === "monthly" && monthlyData && (
        <section className="dashboard__months">
          {monthlyData.months.map((m) => (
            <MonthCard key={m.month} summary={m} />
          ))}
        </section>
      )}

      {showAnnualCost && (
        <AnnualCostModal onClose={() => setShowAnnualCost(false)} />
      )}
    </div>
  );
}
