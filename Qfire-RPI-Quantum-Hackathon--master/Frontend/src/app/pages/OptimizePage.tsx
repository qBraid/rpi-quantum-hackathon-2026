import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, Notice, PageHeader, ScenarioGrid, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

type PlanKey = "recommended" | "corridor" | "containment" | "quantum_informed";

function buildDifferenceLookup(stepRecord: any | null) {
  if (!stepRecord) return {};
  const lookup: Record<string, "protected" | "changed"> = {};
  const baseline = stepRecord.baseline?.grid ?? [];
  const withPlan = stepRecord.with_plan?.grid ?? [];
  for (let row = 0; row < baseline.length; row += 1) {
    for (let col = 0; col < baseline[row].length; col += 1) {
      const left = baseline[row][col];
      const right = withPlan[row]?.[col];
      if (left !== right) {
        lookup[`${row}-${col}`] = left !== "ignition" && left !== "burned" && (right === "ignition" || right === "burned") ? "changed" : "protected";
      }
    }
  }
  return lookup;
}

export function OptimizePage() {
  const [params] = useSearchParams();
  const [scenarioId, setScenarioId] = useState(params.get("scenario") ?? "");
  const [mode, setMode] = useState<"planning" | "challenge">("planning");
  const [budget] = useState(10);
  const [reducedCount, setReducedCount] = useState(12);
  const [run, setRun] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; title: string; description: string } | null>(null);
  const [planView, setPlanView] = useState<PlanKey>("recommended");
  const [playbackStep, setPlaybackStep] = useState(0);
  const { data: scenarios, loading, error } = useAsyncData(api.listScenarios, []);
  const { data: runHistory, loading: historyLoading, reload: reloadHistory } = useAsyncData(
    () => (scenarioId ? api.listOptimizeRuns(scenarioId) : Promise.resolve([])),
    [scenarioId],
  );

  const selectedScenario = useMemo(() => scenarios?.find((scenario) => scenario.id === scenarioId) ?? scenarios?.[0], [scenarioId, scenarios]);
  const activeScenarioId = scenarioId || selectedScenario?.id || "";
  const activeMode = (run?.summary?.mode as "planning" | "challenge" | undefined) ?? mode;

  const planOptions = useMemo(() => {
    if (!run) return [];
    if (activeMode === "challenge") {
      return [{ key: "recommended" as const, label: "Challenge corridor plan" }];
    }
    return [
      { key: "recommended" as const, label: "Recommended" },
      { key: "corridor" as const, label: "Corridor plan" },
      { key: "containment" as const, label: "Containment plan" },
      { key: "quantum_informed" as const, label: "Quantum-informed" },
    ];
  }, [activeMode, run]);

  const selectedPlan = useMemo(() => {
    if (!run) return null;
    if (activeMode === "challenge") return run.results.recommended_plan;
    if (planView === "corridor") return run.results.corridor_plan;
    if (planView === "containment") return run.results.containment_plan;
    if (planView === "quantum_informed") return run.results.quantum_informed;
    return run.results.recommended_plan;
  }, [activeMode, planView, run]);

  const selectedComparison = useMemo(() => {
    if (!run) return null;
    if (activeMode === "challenge") return run.results.comparison_playback;
    if (planView === "corridor") return run.results.plan_comparisons?.corridor ?? run.results.comparison_playback;
    if (planView === "containment") return run.results.plan_comparisons?.containment ?? run.results.comparison_playback;
    if (planView === "quantum_informed") return run.results.plan_comparisons?.quantum_informed ?? run.results.comparison_playback;
    return run.results.comparison_playback;
  }, [activeMode, planView, run]);

  const recommendedPlacements = (selectedPlan?.placements as Array<any> | undefined) ?? [];
  const placementLookup = Object.fromEntries(recommendedPlacements.map((item) => [`${item.row}-${item.col}`, true]));
  const steps = (selectedComparison?.steps as Array<any> | undefined) ?? [];
  const boundedStep = Math.min(playbackStep, Math.max(0, steps.length - 1));
  const activeStep = steps[boundedStep] ?? null;
  const differenceLookup = buildDifferenceLookup(activeStep);

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

  useEffect(() => {
    setPlaybackStep(0);
  }, [run, planView]);

  async function execute() {
    if (!activeScenarioId) return;
    setRunning(true);
    setMessage(null);
    try {
      const response = await api.runOptimize({
        scenario_id: activeScenarioId,
        mode,
        intervention_budget_k: budget,
        reduced_candidate_count: reducedCount,
      });
      setRun(response);
      setPlanView("recommended");
      setMessage({
        tone: "success",
        title: "Intervention plan complete",
        description:
          mode === "challenge"
            ? "The optimizer recomputed the exact challenge-facing adjacency plan and stored side-by-side spread playback for presentation."
            : "The optimizer recomputed corridor and containment plans and stored baseline-vs-plan playback using the shared wildfire model.",
      });
      await reloadHistory();
    } catch (err) {
      setMessage({
        tone: "error",
        title: "Optimization failed",
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <LoadingState label="Loading optimization workspace..." />;
  if (error || !scenarios) return <EmptyState title="Optimization workspace unavailable" description={error ?? "Could not load scenarios."} />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 4 - Intervention Plan"
        title="Intervention planning"
        description={
          activeMode === "challenge"
            ? "Challenge mode matches the posted 10x10 adjacency disruption problem with strict K=10 placement. The side-by-side playback shows how that same placement changes spread under the shared planning-grade forecast."
            : "Planning mode compares corridor-cut and containment-oriented intervention styles, then shows how spread changes without the plan versus with the selected plan."
        }
        actions={
          <button onClick={() => void execute()} disabled={!activeScenarioId || running} className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate disabled:opacity-50">
            {running ? "Running..." : "Generate plan"}
          </button>
        }
      />

      {message ? <Notice tone={message.tone} title={message.title} description={message.description} /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <SectionPanel
            title="Planning inputs"
            subtitle={
              mode === "challenge"
                ? "Challenge mode follows the posted adjacency objective. Planning mode remains the richer forecast-aware analysis."
                : "Planning mode compares two intervention interpretations: corridor disruption and near-front containment."
            }
          >
            <div className="grid gap-4 lg:grid-cols-4">
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
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Mode</label>
                <select value={mode} onChange={(event) => setMode(event.target.value as "planning" | "challenge")} className="w-full border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors">
                  <option value="planning">Planning mode</option>
                  <option value="challenge">Challenge mode</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Budget</label>
                <input value="K = 10" readOnly className="w-full border border-border bg-secondary/50 px-4 py-2.5 text-[14px] font-mono text-muted-foreground outline-none" />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Reduced quantum shortlist</label>
                <input type="number" min={10} max={16} value={reducedCount} onChange={(event) => setReducedCount(Number(event.target.value))} className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors" />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusPill label={mode === "challenge" ? "Challenge mode" : "Planning mode"} tone={mode === "challenge" ? "accent" : "good"} />
              <StatusPill label={mode === "challenge" ? "Exact adjacency objective" : "Corridor + containment comparison"} tone="neutral" />
            </div>
          </SectionPanel>

          {run ? (
            <>
              <SectionPanel title="Plan options" subtitle={activeMode === "challenge" ? "Challenge mode exposes the exact challenge-facing plan." : "Choose which plan style to inspect. The recommendation status still reflects the safer default recommendation logic."}>
                <div className="grid gap-4 md:grid-cols-3">
                  {activeMode === "challenge" ? (
                    <div className="border border-primary bg-secondary/20 p-4">
                      <p className="text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Challenge corridor plan</p>
                      <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{run.summary.plan_explanation}</p>
                    </div>
                  ) : (
                    <>
                      <button onClick={() => setPlanView("corridor")} className={`border p-4 text-left ${planView === "corridor" ? "border-primary bg-secondary/20" : "border-border bg-card"}`}>
                        <p className="text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Corridor plan</p>
                        <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{run.results.corridor_plan?.explanation}</p>
                      </button>
                      <button onClick={() => setPlanView("containment")} className={`border p-4 text-left ${planView === "containment" ? "border-primary bg-secondary/20" : "border-border bg-card"}`}>
                        <p className="text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Containment plan</p>
                        <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{run.results.containment_plan?.explanation}</p>
                      </button>
                      <button onClick={() => setPlanView("recommended")} className={`border p-4 text-left ${planView === "recommended" ? "border-primary bg-secondary/20" : "border-border bg-card"}`}>
                        <p className="text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Recommended default</p>
                        <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{run.summary.recommendation_reason}</p>
                      </button>
                    </>
                  )}
                </div>
              </SectionPanel>

              <SectionPanel title="Why this plan" subtitle="Plain-language explanation of what the system is trying to block or protect">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill
                    label={(run.summary.recommendation_status ?? "recommended").replace("_", " ")}
                    tone={run.summary.recommendation_status === "recommended" ? "good" : run.summary.recommendation_status === "tradeoff" ? "warn" : "neutral"}
                  />
                  <StatusPill label={activeMode === "challenge" ? "Challenge corridor plan" : selectedPlan?.plan_label ?? run.summary.recommended_plan_type ?? "Plan"} tone="accent" />
                </div>
                <p className="mt-3 text-[14px] leading-relaxed text-muted-foreground">
                  {selectedPlan?.explanation ?? run.summary.plan_explanation ?? run.summary.recommendation_reason}
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-4">
                  {activeMode === "challenge" ? (
                    <>
                      <MetricTile label="Challenge cost" value={String(run.summary.challenge_cost_after)} hint="Lower is better on the posted objective" />
                      <MetricTile label="Disrupted edges" value={String(run.summary.disrupted_edges)} hint="Removed dry-brush fire-path links" />
                      <MetricTile label="K used" value={String(run.summary.K_used)} hint="Strict placement count" />
                      <MetricTile label="Quantum shortlist" value={String(run.summary.reduced_quantum_scope.shortlist_count)} hint="Reduced graph for tractable QAOA analysis" />
                    </>
                  ) : (
                    <>
                      <MetricTile label="Mean burned area" value={`${run.summary.after_mean_burned_area}`} hint={`Baseline ${run.summary.before_mean_burned_area}`} />
                      <MetricTile label="P90 burned area" value={`${run.summary.after_p90_burned_area}`} hint={`Baseline ${run.summary.before_p90_burned_area}`} />
                      <MetricTile label="Corridor disruption" value={String(run.summary.corridor_disruption)} hint="Spread-path disruption" />
                      <MetricTile label="High-risk cells covered" value={String(run.summary.high_risk_region_protection)} hint="Cells under high burn probability touched by the plan" />
                    </>
                  )}
                </div>
              </SectionPanel>

              <SectionPanel title="Selected interventions" subtitle="Treated cells are shown with a distinct treatment marker so the mitigation pattern is easy to read">
                <ScenarioGrid grid={selectedScenario?.grid ?? []} interventionLookup={placementLookup} />
              </SectionPanel>

              <SectionPanel title="Baseline spread vs spread with plan" subtitle="Both views use the same forecast settings and the same synchronized step slider">
                <div className="mb-4 flex flex-col gap-3 border border-border bg-card p-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Shared playback step</p>
                    <p className="mt-1 text-[13px] text-muted-foreground">Step {boundedStep} / {Math.max(steps.length - 1, 0)}</p>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(steps.length - 1, 0)}
                    value={boundedStep}
                    onChange={(event) => setPlaybackStep(Number(event.target.value))}
                    className="w-full md:max-w-[420px]"
                  />
                </div>
                <div className="grid gap-6 xl:grid-cols-2">
                  <div>
                    <p className="mb-3 text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Baseline spread</p>
                    <ScenarioGrid grid={(activeStep?.baseline?.grid as any) ?? (selectedScenario?.grid ?? [])} differenceLookup={differenceLookup} />
                  </div>
                  <div>
                    <p className="mb-3 text-[12px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Spread with plan</p>
                    <ScenarioGrid grid={(activeStep?.with_plan?.grid as any) ?? (selectedScenario?.grid ?? [])} interventionLookup={placementLookup} differenceLookup={differenceLookup} />
                  </div>
                </div>
              </SectionPanel>

              <SectionPanel title="Difference summary" subtitle="Compact summary of what changed when the selected plan was applied">
                <div className="grid gap-4 md:grid-cols-5">
                  <MetricTile label="Protected cells" value={String(selectedComparison?.difference_summary?.protected_cells_by_threshold ?? 0)} hint="Dropped below high-risk threshold" />
                  <MetricTile label="Delayed ignition" value={String(selectedComparison?.difference_summary?.delayed_ignition_cells ?? 0)} hint="Cells igniting at least one step later" />
                  <MetricTile label="Reduced corridor cells" value={String(selectedComparison?.difference_summary?.reduced_spread_corridor_cells ?? 0)} hint="Likely spread-corridor cells removed" />
                  <MetricTile label="Mean area delta" value={String(selectedComparison?.difference_summary?.mean_burned_area_difference ?? 0)} hint="Baseline minus with-plan" />
                  <MetricTile label="P90 delta" value={String(selectedComparison?.difference_summary?.p90_burned_area_difference ?? 0)} hint="Risk-sensitive area reduction" />
                </div>
                <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
                  {(selectedComparison?.difference_summary?.material_outperformance ?? false)
                    ? "The selected plan produces a material spread improvement under the shared planning forecast."
                    : "The selected plan changes spread structure, but the improvement over baseline is modest under the current settings."}
                </p>
              </SectionPanel>

              <SectionPanel title="Classical full-grid vs reduced quantum study" subtitle={activeMode === "challenge" ? "The quantum subproblem is carved from the same posted challenge graph." : "The reduced quantum study remains tied to the same candidate graph and is shown separately from the deployable plan style."}>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Full-grid classical layer</p>
                    <p className="text-[13px] leading-relaxed text-foreground">{run.summary.full_scale_scope}</p>
                  </div>
                  <div className="border border-border bg-card p-5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 border-b border-border pb-2">Reduced quantum layer</p>
                    <p className="text-[13px] leading-relaxed text-foreground">{run.summary.reduced_quantum_scope.note}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <StatusPill label={`Shortlist ${run.summary.reduced_quantum_scope.shortlist_count}`} tone="neutral" />
                      <StatusPill label={`Subgraph ${run.summary.reduced_quantum_scope.candidate_count}`} tone="accent" />
                      <StatusPill label={`Approx ratio ${(run.results.quantum.approximation_ratio * 100).toFixed(1)}%`} tone="good" />
                    </div>
                  </div>
                </div>
              </SectionPanel>

              <SectionPanel title="Placement explanations" subtitle="Each intervention is tied to the blocking logic of the selected plan">
                <div className="space-y-4">
                  {recommendedPlacements.length === 0 ? (
                    <p className="text-[13px] text-muted-foreground">No deployable plan is marked as recommended under the current safety rules.</p>
                  ) : (
                    recommendedPlacements.slice(0, budget).map((placement) => (
                      <div key={`${placement.row}-${placement.col}`} className="border border-border bg-card p-5 border-l-2 border-l-qp-cyan">
                        <p className="text-[14px] font-bold text-foreground mb-1">Row {placement.row + 1}, Col {placement.col + 1}</p>
                        <p className="text-[13px] leading-relaxed text-muted-foreground">{placement.reason}</p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {activeMode === "challenge" ? (
                            <>
                              <StatusPill label={`Adjacency degree ${placement.challenge_degree ?? 0}`} tone="warn" />
                              <StatusPill label={`Disrupted edges ${placement.challenge_disrupted_edges ?? 0}`} tone="good" />
                            </>
                          ) : (
                            <>
                              <StatusPill label={`Burn prob ${((placement.burn_probability ?? 0) * 100).toFixed(0)}%`} tone="warn" />
                              <StatusPill label={`Ignition delay ${placement.ignition_delay ?? 0}`} tone="good" />
                            </>
                          )}
                          {placement.selected_by_quantum ? <StatusPill label="Supported by reduced quantum study" tone="accent" /> : <StatusPill label="Classical placement" tone="neutral" />}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </SectionPanel>
            </>
          ) : (
            <EmptyState title="No intervention plan yet" description="Run planning mode for corridor-vs-containment comparison or challenge mode for the exact 10x10 adjacency disruption formulation." />
          )}
        </div>

        <SectionPanel title="Recent intervention plans" subtitle={historyLoading ? "Loading scenario history..." : "Saved optimization runs for this scenario"}>
          <div className="space-y-3">
            {(runHistory ?? []).length === 0 ? (
              <p className="text-[12px] text-muted-foreground">No optimization runs saved for this scenario yet.</p>
            ) : (
              (runHistory ?? []).slice(0, 8).map((item) => (
                <button key={item.id} onClick={() => setRun(item)} className={`w-full border p-4 text-left transition-colors ${run?.id === item.id ? "border-primary bg-secondary/30" : "border-border bg-card hover:border-primary/50"}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[13px] font-bold">{item.id.slice(0, 8)}</p>
                      <p className="mt-1 text-[11px] text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                    <StatusPill label={`${item.summary?.mode ?? "planning"} • ${item.summary?.recommendation_status ?? item.summary?.recommended_mode ?? item.status}`} tone="accent" />
                  </div>
                </button>
              ))
            )}
          </div>
          {run ? (
            <div className="mt-8 pt-6 border-t border-border flex flex-col gap-3">
              <p className="text-[12px] uppercase tracking-[0.15em] font-bold text-foreground">Next steps</p>
              <div className="flex flex-wrap gap-2">
                <Link to={`/app/benchmarks?scenario=${activeScenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                  Benchmarks
                </Link>
              </div>
            </div>
          ) : null}
        </SectionPanel>
      </div>
    </div>
  );
}
