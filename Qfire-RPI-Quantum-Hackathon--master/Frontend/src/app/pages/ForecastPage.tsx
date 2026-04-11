import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, Notice, PageHeader, ScenarioGrid, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

export function ForecastPage() {
  const [params] = useSearchParams();
  const [scenarioId, setScenarioId] = useState(params.get("scenario") ?? "");
  const [steps, setSteps] = useState(6);
  const [dryness, setDryness] = useState(0.78);
  const [spreadSensitivity, setSpreadSensitivity] = useState(0.64);
  const [windDirection, setWindDirection] = useState("NE");
  const [ensembleRuns, setEnsembleRuns] = useState(24);
  const [timelineStep, setTimelineStep] = useState(0);
  const [run, setRun] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; title: string; description: string } | null>(null);
  const { data: scenarios, loading, error } = useAsyncData(api.listScenarios, []);
  const { data: runHistory, loading: historyLoading, reload: reloadHistory } = useAsyncData(
    () => (scenarioId ? api.listForecastRuns(scenarioId) : Promise.resolve([])),
    [scenarioId],
  );

  const selectedScenario = useMemo(() => scenarios?.find((scenario) => scenario.id === scenarioId) ?? scenarios?.[0], [scenarioId, scenarios]);
  const activeScenarioId = scenarioId || selectedScenario?.id || "";
  const activeSnapshot = run?.snapshots?.[timelineStep] ?? null;
  const probabilityLookup = Object.fromEntries((run?.diagnostics?.ensemble?.burn_probability_map ?? []).map((item: any) => [`${item.row}-${item.col}`, item.probability]));

  useEffect(() => {
    if (selectedScenario && !scenarioId) {
      setScenarioId(selectedScenario.id);
    }
  }, [scenarioId, selectedScenario]);

  useEffect(() => {
    if (runHistory && runHistory.length > 0 && !run) {
      setRun(runHistory[0]);
    }
  }, [runHistory, run]);

  async function execute() {
    if (!activeScenarioId) return;
    setRunning(true);
    setMessage(null);
    try {
      const response = await api.runForecast({
        scenario_id: activeScenarioId,
        steps,
        dryness,
        spread_sensitivity: spreadSensitivity,
        wind_direction: windDirection,
        ensemble_runs: ensembleRuns,
      });
      setRun(response);
      setTimelineStep(0);
      setMessage({
        tone: "success",
        title: "Ensemble forecast complete",
        description: `${response.summary?.ensemble_runs ?? ensembleRuns} stochastic runs summarized for planning use.`,
      });
      await reloadHistory();
    } catch (err) {
      setMessage({
        tone: "error",
        title: "Forecast failed",
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <LoadingState label="Loading forecast workspace..." />;
  if (error || !scenarios) return <EmptyState title="Forecast workspace unavailable" description={error ?? "Could not load scenarios."} />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 3 - Forecast"
        title="Ensemble spread forecast"
        description="Run a stochastic ensemble to estimate burn probability, likely ignition timing, and likely spread corridors. This is planning-grade comparative support, not live fire prediction."
        actions={
          <button onClick={() => void execute()} disabled={!activeScenarioId || running} className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate disabled:opacity-50">
            {running ? "Running..." : "Run forecast"}
          </button>
        }
      />

      {message ? <Notice tone={message.tone} title={message.title} description={message.description} /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <SectionPanel title="Forecast inputs" subtitle="Environmental assumptions are used consistently across risk, forecast, and optimization">
            <div className="grid gap-4 lg:grid-cols-6">
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Scenario</label>
                <select value={activeScenarioId} onChange={(event) => setScenarioId(event.target.value)} className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors">
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Steps</label>
                <input type="number" min={2} max={12} value={steps} onChange={(event) => setSteps(Number(event.target.value))} className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors" />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Dryness</label>
                <input type="number" step="0.01" min={0} max={1} value={dryness} onChange={(event) => setDryness(Number(event.target.value))} className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors" />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Sensitivity</label>
                <input type="number" step="0.01" min={0} max={1} value={spreadSensitivity} onChange={(event) => setSpreadSensitivity(Number(event.target.value))} className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors" />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Wind</label>
                <select value={windDirection} onChange={(event) => setWindDirection(event.target.value)} className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors">
                  {["N", "S", "E", "W", "NE", "NW", "SE", "SW"].map((direction) => (
                    <option key={direction} value={direction}>
                      {direction}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Ensemble runs</label>
                <input type="number" min={8} max={64} value={ensembleRuns} onChange={(event) => setEnsembleRuns(Number(event.target.value))} className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors" />
              </div>
            </div>
          </SectionPanel>

          {run ? (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <MetricTile label="Mean burned area" value={String(run.summary.mean_final_burned_area)} hint={`P90 ${run.summary.burned_area_p90}`} />
                <MetricTile label="Peak burn probability" value={`${((run.summary.peak_burn_probability ?? 0) * 100).toFixed(0)}%`} hint={run.summary.containment_outlook} />
                <MetricTile label="Ensemble runs" value={String(run.summary.ensemble_runs)} hint="Independent stochastic realizations" />
                <MetricTile label="Representative step" value={`${timelineStep}/${(run.snapshots?.length ?? 1) - 1}`} hint="Median-like sample run" />
              </div>

              <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                <SectionPanel title="Representative spread run" subtitle="One representative stochastic run, shown for interpretation only">
                  <ScenarioGrid grid={activeSnapshot?.grid ?? selectedScenario?.grid ?? []} />
                  <input type="range" min={0} max={(run.snapshots?.length ?? 1) - 1} value={timelineStep} onChange={(event) => setTimelineStep(Number(event.target.value))} className="mt-5 w-full accent-qp-cyan" />
                </SectionPanel>

                <SectionPanel title="Burn probability map" subtitle="Aggregate ignition likelihood across the full ensemble">
                  <ScenarioGrid grid={selectedScenario?.grid ?? []} scoreLookup={probabilityLookup} />
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <MetricTile label="P10 area" value={String(run.diagnostics.ensemble.final_burned_area_distribution ? Math.min(...run.diagnostics.ensemble.final_burned_area_distribution) : 0)} />
                    <MetricTile label="P90 area" value={String(run.summary.burned_area_p90)} />
                  </div>
                </SectionPanel>
              </div>

              <SectionPanel title="Uncertainty and corridors" subtitle="These outputs show where the ensemble repeatedly burns or ignites early">
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Likely spread corridors</p>
                    <ul className="space-y-2 text-[12px] text-muted-foreground leading-relaxed">
                      {(run.summary.likely_spread_corridors ?? []).slice(0, 6).map((cell: any) => (
                        <li key={`${cell.row}-${cell.col}`}>Row <span className="font-semibold text-foreground">{cell.row + 1}</span>, Col <span className="font-semibold text-foreground">{cell.col + 1}</span> • <span className="text-qp-red">{(cell.frequency * 100).toFixed(0)}% of runs</span></li>
                      ))}
                    </ul>
                  </div>
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Model framing</p>
                    <p className="text-[13px] leading-relaxed text-muted-foreground">{run.summary.planning_grade_note}</p>
                    <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">Dryness, wind, slope proxy, and spotting are all treated as uncertain within the ensemble rather than fixed truth.</p>
                  </div>
                </div>
              </SectionPanel>
            </>
          ) : (
            <EmptyState title="No forecast run yet" description="Run the ensemble forecast to estimate burn probability, expected ignition timing, and burned-area uncertainty for this scenario." />
          )}
        </div>

        <SectionPanel title="Recent forecasts" subtitle={historyLoading ? "Loading scenario history..." : "Saved ensemble forecasts for this scenario"}>
          <div className="space-y-3">
            {(runHistory ?? []).length === 0 ? (
              <p className="text-[12px] text-muted-foreground">No forecast runs saved for this scenario yet.</p>
            ) : (
              (runHistory ?? []).slice(0, 8).map((item) => (
                <button key={item.id} onClick={() => { setRun(item); setTimelineStep(0); }} className={`w-full border p-4 text-left transition-colors ${run?.id === item.id ? "border-primary bg-secondary/30" : "border-border bg-card hover:border-primary/50"}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[13px] font-bold">{item.id.slice(0, 8)}</p>
                      <p className="mt-1 text-[11px] text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                    <StatusPill label={item.summary?.containment_outlook ?? item.status} tone="accent" />
                  </div>
                </button>
              ))
            )}
          </div>
          {run ? (
            <div className="mt-8 pt-6 border-t border-border flex flex-col gap-3">
              <p className="text-[12px] uppercase tracking-[0.15em] font-bold text-foreground">Next steps</p>
              <div className="flex flex-wrap gap-2">
                <Link to={`/app/optimize?scenario=${activeScenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                  Optimize
                </Link>
                <Link to={`/app/reports?scenario=${activeScenarioId}&forecast=${run.id}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                  Report with this run
                </Link>
              </div>
            </div>
          ) : null}
        </SectionPanel>
      </div>
    </div>
  );
}
