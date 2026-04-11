import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, Notice, PageHeader, ScenarioGrid, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

const MODE_META = {
  classical: { title: "Classical ML", subtitle: "Logistic regression baseline" },
  quantum: { title: "Quantum ML", subtitle: "Qiskit variational classifier" },
  hybrid: { title: "Hybrid view", subtitle: "Probability ensemble on the same task" },
} as const;

function modeLabel(mode: string) {
  return MODE_META[mode as keyof typeof MODE_META]?.title ?? mode;
}

export function RiskPage() {
  const [params] = useSearchParams();
  const seededScenario = params.get("scenario") ?? "";
  const [scenarioId, setScenarioId] = useState(seededScenario);
  const [run, setRun] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [horizonSteps, setHorizonSteps] = useState(2);
  const [sampleCount, setSampleCount] = useState(24);
  const [message, setMessage] = useState<{ tone: "success" | "error"; title: string; description: string } | null>(null);
  const { data: scenarios, loading, error } = useAsyncData(api.listScenarios, []);
  const { data: runHistory, loading: historyLoading, reload: reloadHistory } = useAsyncData(
    () => (scenarioId ? api.listRiskRuns(scenarioId) : Promise.resolve([])),
    [scenarioId],
  );

  const selectedScenario = useMemo(() => scenarios?.find((scenario) => scenario.id === scenarioId) ?? scenarios?.[0], [scenarioId, scenarios]);
  const activeScenarioId = scenarioId || selectedScenario?.id || "";

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
      const response = await api.runRisk({ scenario_id: activeScenarioId, horizon_steps: horizonSteps, sample_count: sampleCount });
      setRun(response);
      setScenarioId(activeScenarioId);
      setMessage({
        tone: "success",
        title: "Risk classification run complete",
        description: `${response.summary?.recommended_mode ?? "A model"} delivered the best held-out F1. The run is now saved in scenario history.`,
      });
      await reloadHistory();
    } catch (err) {
      setMessage({
        tone: "error",
        title: "Risk run failed",
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <LoadingState label="Loading risk workspace..." />;
  if (error || !scenarios) return <EmptyState title="Risk workspace unavailable" description={error ?? "Could not load scenarios."} />;

  const availableModes = (["classical", "quantum", "hybrid"] as const).filter((mode) => run?.results?.[mode]);
  const dataset = run?.summary?.dataset;
  const scoreLookup = (mode: string) =>
    Object.fromEntries((run?.results?.[mode]?.grid_scores ?? []).map((item: any) => [`${item.row}-${item.col}`, item.score]));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 2 - Risk Map"
        title="Early ignition corridor classification"
        description="Train a classical baseline and a real Qiskit QML model on the same wildfire task: predict which cells are likely to join an early ignition corridor under the shared ensemble hazard model."
        actions={
          <button onClick={() => void execute()} disabled={!activeScenarioId || running} className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate disabled:opacity-50">
            {running ? "Running..." : "Run classification"}
          </button>
        }
      />

      {message ? <Notice tone={message.tone} title={message.title} description={message.description} /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <SectionPanel title="Task setup" subtitle="Same dataset, same label, same evaluation split">
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px_180px]">
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Scenario</label>
                <select
                  value={activeScenarioId}
                  onChange={(event) => setScenarioId(event.target.value)}
                  className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors"
                >
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Response window</label>
                <select
                  value={String(horizonSteps)}
                  onChange={(event) => setHorizonSteps(Number(event.target.value))}
                  className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors"
                >
                  <option value="2">2 steps</option>
                  <option value="3">3 steps</option>
                  <option value="4">4 steps</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Simulation draws</label>
                <select
                  value={String(sampleCount)}
                  onChange={(event) => setSampleCount(Number(event.target.value))}
                  className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors"
                >
                  <option value="16">16</option>
                  <option value="24">24</option>
                  <option value="32">32</option>
                </select>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MetricTile label="Binary target" value="Corridor" hint="Will this cell join the early ignition corridor?" />
              <MetricTile label="Classical model" value="LogReg" hint="Scaled logistic regression baseline" />
              <MetricTile label="Quantum model" value="QML" hint="Shallow Qiskit variational classifier" />
            </div>
          </SectionPanel>

          {run ? (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <MetricTile label="Recommended model" value={String(run.summary.recommended_mode).toUpperCase()} hint="Best held-out tradeoff for this run" />
                <MetricTile label="Most practical" value={String(run.summary.most_practical_mode).toUpperCase()} hint="Best repeat-use choice under current cost" />
                <MetricTile label="Training samples" value={String(dataset?.train_samples ?? "0")} hint={`${dataset?.positive_samples ?? 0} positive / ${dataset?.negative_samples ?? 0} negative labels`} />
                <MetricTile label="Effective window" value={`${dataset?.effective_label_horizon_steps ?? horizonSteps} steps`} hint="Actual label horizon used to keep the split meaningful" />
              </div>

              <SectionPanel title="Dataset and task" subtitle="Generated from the same stochastic wildfire model used by forecast and optimization">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Classification target</p>
                    <p className="text-[14px] font-semibold text-foreground mb-1">{run.summary.classification_task}</p>
                    <p className="text-[13px] leading-relaxed text-muted-foreground">{dataset?.label_definition}</p>
                  </div>
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Features</p>
                    <p className="text-[14px] font-semibold text-foreground mb-1">{(dataset?.feature_names ?? []).join(", ")}</p>
                    <p className="text-[13px] leading-relaxed text-muted-foreground">{dataset?.dataset_generation}</p>
                  </div>
                </div>
              </SectionPanel>

              <SectionPanel title="Held-out model comparison" subtitle="All models are evaluated on the same test split.">
                <div className="grid gap-4 lg:grid-cols-3">
                  {(run.summary.comparison as Array<any>).map((item) => (
                    <div key={item.mode} className="border border-border bg-card p-5 shadow-sm">
                      <div className="flex items-center justify-between gap-3 border-b border-border pb-3 mb-4">
                        <div>
                          <p className="text-[15px] font-bold tracking-tight">{modeLabel(item.mode)}</p>
                          <p className="mt-1 text-[12px] text-muted-foreground italic">{run.results[item.mode]?.model?.notes}</p>
                        </div>
                        <StatusPill label={item.mode === run.summary.recommended_mode ? "Best quality" : item.mode === run.summary.most_practical_mode ? "Most practical" : "Compared"} tone={item.mode === run.summary.recommended_mode ? "good" : "accent"} />
                      </div>
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <MetricTile label="Accuracy" value={(item.accuracy * 100).toFixed(1)} hint="Held-out split" />
                        <MetricTile label="F1" value={(item.f1 * 100).toFixed(1)} hint="Balanced quality summary" />
                        <MetricTile label="Precision" value={(item.precision * 100).toFixed(1)} hint="Positive prediction quality" />
                        <MetricTile label="Recall" value={(item.recall * 100).toFixed(1)} hint="High-risk cell capture" />
                      </div>
                      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{item.runtime_ms} ms • {item.practicality}</p>
                    </div>
                  ))}
                </div>
              </SectionPanel>

              <div className="grid gap-6 xl:grid-cols-3">
                {availableModes.map((mode) => (
                  <SectionPanel key={mode} title={`${MODE_META[mode].title} risk map`} subtitle={MODE_META[mode].subtitle}>
                    <ScenarioGrid grid={selectedScenario?.grid ?? []} scoreLookup={scoreLookup(mode)} />
                    <div className="mt-4 space-y-2 text-[12px] text-muted-foreground">
                      <p>Accuracy {(run.results[mode].metrics.accuracy * 100).toFixed(1)}%</p>
                      <p>F1 {(run.results[mode].metrics.f1 * 100).toFixed(1)}%</p>
                      <p>{run.results[mode].metrics.practicality}</p>
                    </div>
                  </SectionPanel>
                ))}
              </div>

              <SectionPanel title="Hotspots and conclusion" subtitle="Highest predicted early-corridor probabilities for this scenario">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill label={`Recommended: ${run.summary.recommended_mode}`} tone="good" />
                  <StatusPill label={`Practical: ${run.summary.most_practical_mode}`} tone="accent" />
                </div>
                <p className="mt-4 text-[13px] text-muted-foreground">{run.summary.conclusion}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {availableModes.map((mode) => (
                    <div key={mode} className="border border-border bg-card p-5">
                      <p className="text-[13px] font-bold uppercase tracking-wide text-foreground border-b border-border pb-2 mb-3">{MODE_META[mode].title}</p>
                      <ul className="space-y-2 text-[12px] text-muted-foreground leading-relaxed">
                        {(run.results[mode].top_hotspots as Array<any>).slice(0, 4).map((hotspot) => (
                          <li key={`${mode}-${hotspot.row}-${hotspot.col}`}>
                            Row <span className="font-semibold text-foreground">{hotspot.row + 1}</span>, Col <span className="font-semibold text-foreground">{hotspot.col + 1}</span> • <span className="text-qp-red">{(hotspot.score * 100).toFixed(0)}% corridor risk</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </SectionPanel>

              <SectionPanel title="Continue workflow" subtitle="Use this run as the risk evidence for the same hillside version.">
                <div className="flex flex-wrap gap-2">
                  <Link to={`/app/forecast?scenario=${activeScenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-5 py-2.5 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Spread forecast
                  </Link>
                  <Link to={`/app/reports?scenario=${activeScenarioId}&risk=${run.id}`} className="border border-border bg-secondary/50 hover:bg-secondary px-5 py-2.5 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Report with this run
                  </Link>
                </div>
              </SectionPanel>
            </>
          ) : (
            <EmptyState
              title="No risk classification run yet"
              description="Run the classifier comparison to see which cells are most likely to join an early spread corridor and whether the classical or quantum model is more useful for planning."
            />
          )}
        </div>

        <SectionPanel title="Recent risk runs" subtitle={historyLoading ? "Loading scenario history..." : "Saved classifier comparisons for this scenario"}>
          <div className="space-y-3">
            {(runHistory ?? []).length === 0 ? (
              <p className="text-[12px] text-muted-foreground">No risk runs saved for this scenario yet.</p>
            ) : (
              (runHistory ?? []).slice(0, 8).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setRun(item)}
                    className={`w-full border p-4 text-left transition-colors ${run?.id === item.id ? "border-primary bg-secondary/30" : "border-border bg-card hover:border-primary/50"}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[13px] font-bold">{item.id.slice(0, 8)}</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                      </div>
                      <StatusPill label={item.summary?.recommended_mode ?? item.status} tone="accent" />
                    </div>
                    <p className="mt-2 text-[12px] text-muted-foreground leading-relaxed">{item.summary?.classification_task ?? "Binary corridor classification"}</p>
                  </button>
              ))
            )}
          </div>
        </SectionPanel>
      </div>
    </div>
  );
}
