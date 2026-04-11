import { useEffect, useMemo, useState } from "react";
import { Download, FileText } from "lucide-react";
import { useSearchParams } from "react-router";

import { api } from "../api";
import { EmptyState, LoadingState, Notice, PageHeader, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

function normalizeSeed(value: string | null) {
  return value && value.length > 0 ? value : "";
}

export function ReportsPage() {
  const [params] = useSearchParams();
  const [scenarioId, setScenarioId] = useState(normalizeSeed(params.get("scenario")));
  const [riskRunId, setRiskRunId] = useState(normalizeSeed(params.get("risk")));
  const [forecastRunId, setForecastRunId] = useState(normalizeSeed(params.get("forecast")));
  const [optimizationRunId, setOptimizationRunId] = useState(normalizeSeed(params.get("optimization")));
  const [benchmarkRunId, setBenchmarkRunId] = useState(normalizeSeed(params.get("benchmark")));
  const [activeReport, setActiveReport] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; title: string; description: string } | null>(null);

  const { data: scenarios, loading: scenariosLoading, error: scenariosError } = useAsyncData(api.listScenarios, []);
  const { data: reports, loading: reportsLoading, reload: reloadReports } = useAsyncData(
    () => api.listReports(scenarioId || undefined),
    [scenarioId],
  );
  const { data: riskRuns } = useAsyncData(() => (scenarioId ? api.listRiskRuns(scenarioId) : Promise.resolve([])), [scenarioId]);
  const { data: forecastRuns } = useAsyncData(() => (scenarioId ? api.listForecastRuns(scenarioId) : Promise.resolve([])), [scenarioId]);
  const { data: optimizeRuns } = useAsyncData(() => (scenarioId ? api.listOptimizeRuns(scenarioId) : Promise.resolve([])), [scenarioId]);
  const { data: benchmarkRuns } = useAsyncData(() => (scenarioId ? api.listBenchmarks(scenarioId) : Promise.resolve([])), [scenarioId]);

  const selectedScenario = useMemo(() => scenarios?.find((scenario) => scenario.id === scenarioId) ?? scenarios?.[0], [scenarioId, scenarios]);
  const activeScenarioId = scenarioId || selectedScenario?.id || "";

  useEffect(() => {
    if (selectedScenario && !scenarioId) {
      setScenarioId(selectedScenario.id);
    }
  }, [scenarioId, selectedScenario]);

  useEffect(() => {
    if (reports && reports.length > 0 && !activeReport) {
      setActiveReport(reports[0]);
    }
  }, [reports, activeReport]);

  async function generate() {
    if (!activeScenarioId) return;
    setRunning(true);
    setMessage(null);
    try {
      const report = await api.generateReport({
        scenario_id: activeScenarioId,
        risk_run_id: riskRunId || null,
        forecast_run_id: forecastRunId || null,
        optimization_run_id: optimizationRunId || null,
        benchmark_run_id: benchmarkRunId || null,
        title: "Wildfire decision report",
      });
      setActiveReport(report);
      await reloadReports();
      setMessage({
        tone: "success",
        title: "Report generated",
        description: "The report now reflects the explicit run selections shown in this workspace.",
      });
    } catch (err) {
      setMessage({
        tone: "error",
        title: "Report generation failed",
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  function exportFile(type: "markdown" | "json") {
    if (!activeReport) return;
    const content =
      type === "markdown"
        ? activeReport.export.content
        : JSON.stringify(
            {
              title: activeReport.title,
              scenario_id: activeReport.scenario_id,
              created_at: activeReport.created_at,
              sections: activeReport.sections,
            },
            null,
            2,
          );
    const blob = new Blob([content], { type: type === "markdown" ? "text/markdown;charset=utf-8" : "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = type === "markdown" ? activeReport.export.filename : `${activeReport.id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (scenariosLoading || reportsLoading) return <LoadingState label="Loading report workspace..." />;
  if (scenariosError || !scenarios || !reports || !riskRuns || !forecastRuns || !optimizeRuns || !benchmarkRuns) {
    return <EmptyState title="Reports unavailable" description={scenariosError ?? "Could not load report dependencies."} />;
  }

  const sections = activeReport?.sections ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 6 - Reports"
        title="Decision reports"
        description="Assemble a wildfire planning brief from explicit scenario-linked runs so planners and research teams can review one coherent recommendation trail."
        actions={
          <button onClick={() => void generate()} disabled={running} className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate disabled:opacity-50">
            {running ? "Generating..." : "Generate report"}
          </button>
        }
      />

      {message ? <Notice tone={message.tone} title={message.title} description={message.description} /> : null}

      <SectionPanel title="Report inputs" subtitle="Choose the scenario and exact evidence you want included in the decision brief">
        <div className="grid gap-4 lg:grid-cols-5">
          <Selector label="Scenario" value={activeScenarioId} onChange={setScenarioId} options={scenarios.map((scenario) => ({ value: scenario.id, label: scenario.name }))} />
          <Selector label="Risk run" value={riskRunId} onChange={setRiskRunId} allowLatest options={riskRuns.map((run) => ({ value: run.id, label: `${run.id.slice(0, 8)} • ${new Date(run.created_at).toLocaleString()}` }))} />
          <Selector label="Forecast run" value={forecastRunId} onChange={setForecastRunId} allowLatest options={forecastRuns.map((run) => ({ value: run.id, label: `${run.id.slice(0, 8)} • ${new Date(run.created_at).toLocaleString()}` }))} />
          <Selector label="Optimization run" value={optimizationRunId} onChange={setOptimizationRunId} allowLatest options={optimizeRuns.map((run) => ({ value: run.id, label: `${run.id.slice(0, 8)} • ${new Date(run.created_at).toLocaleString()}` }))} />
          <Selector label="Benchmark run" value={benchmarkRunId} onChange={setBenchmarkRunId} allowLatest options={benchmarkRuns.map((run) => ({ value: run.id, label: `${run.id.slice(0, 8)} • ${new Date(run.created_at).toLocaleString()}` }))} />
        </div>
      </SectionPanel>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionPanel title="Saved reports" subtitle="Previously generated planning briefs for the selected scenario">
          <div className="space-y-3">
            {reports.length === 0 ? (
              <p className="py-4 text-center text-[13px] text-muted-foreground">No reports generated yet for this scenario.</p>
            ) : (
              reports.map((report) => (
                <button
                  key={report.id}
                  onClick={() => setActiveReport(report)}
                  className={`w-full border p-4 text-left transition-colors ${activeReport?.id === report.id ? "border-primary bg-secondary/30" : "border-border bg-card hover:border-primary/50"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-[13px] font-bold text-foreground">{report.title}</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">{new Date(report.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <StatusPill label={report.status} tone="good" />
                  </div>
                </button>
              ))
            )}
          </div>
        </SectionPanel>

        {activeReport ? (
          <SectionPanel title="Report preview" subtitle={activeReport.title}>
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => exportFile("markdown")}
                  className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground hover:bg-secondary transition-colors"
                >
                  <Download className="h-4 w-4" /> Export markdown
                </button>
                <button
                  onClick={() => exportFile("json")}
                  className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground hover:bg-secondary transition-colors"
                >
                  <Download className="h-4 w-4" /> Export JSON
                </button>
              </div>

              {sections ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <SummaryCard label="Risk map" value={sections.risk?.recommended_mode ?? "Not run"} />
                    <SummaryCard label="Spread forecast" value={sections.forecast?.containment_outlook ?? "Not run"} />
                    <SummaryCard label="Intervention plan" value={sections.optimization?.recommended_mode ?? "Not run"} />
                    <SummaryCard label="Benchmark evidence" value={sections.benchmark_detail?.best_strategy ?? sections.benchmark_detail?.status ?? "Not run"} />
                  </div>

                  {sections.executive_summary ? <ReportListCard title="Executive summary" items={sections.executive_summary as string[]} /> : null}

                  {sections.methodology ? <ReportListCard title="Methodology" items={sections.methodology as string[]} /> : null}

                  <details>
                    <summary className="cursor-pointer text-[11px] font-bold uppercase tracking-wider text-muted-foreground hover:text-primary transition-colors">View raw markdown</summary>
                    <div className="mt-3 border border-border bg-slate-950 p-5 text-[12px] font-mono leading-relaxed text-slate-100">
                      <pre className="whitespace-pre-wrap">{activeReport.export.content}</pre>
                    </div>
                  </details>
                </div>
              ) : null}
            </div>
          </SectionPanel>
        ) : (
          <EmptyState title="No report selected" description="Generate or open a decision brief to preview the recommendation trail and export it." />
        )}
      </div>
    </div>
  );
}

function Selector({
  label,
  value,
  onChange,
  options,
  allowLatest = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  allowLatest?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">{label}</label>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors">
        {allowLatest ? <option value="">Use latest available</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border bg-card p-5">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
      <p className="text-[14px] font-medium text-foreground">{value}</p>
    </div>
  );
}

function ReportListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="border border-border bg-card p-5">
      <h3 className="text-[13px] font-bold uppercase tracking-wider text-foreground mb-3 border-b border-border pb-2">{title}</h3>
      <ul className="space-y-3 text-[13px] leading-relaxed text-muted-foreground">
        {items.map((line, idx) => (
          <li key={idx} className="flex gap-3">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 bg-primary" />
            <span className="text-foreground">{line}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
