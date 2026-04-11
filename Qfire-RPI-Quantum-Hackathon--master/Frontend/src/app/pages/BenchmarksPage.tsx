import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, Notice, PageHeader, SectionPanel, SimulatorBanner, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

export function BenchmarksPage() {
  const [params] = useSearchParams();
  const [scenarioId, setScenarioId] = useState(params.get("scenario") ?? "");
  const [latestRun, setLatestRun] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; title: string; description: string } | null>(null);
  const { data: scenarios, loading: scenariosLoading, error: scenariosError } = useAsyncData(api.listScenarios, []);
  const { data: integrations, loading: integrationsLoading } = useAsyncData(api.integrations, []);
  const { data: benchmarks, loading: benchmarksLoading, reload: reloadBenchmarks } = useAsyncData(
    () => (scenarioId ? api.listBenchmarks(scenarioId) : Promise.resolve([])),
    [scenarioId],
  );

  const selectedScenario = useMemo(() => scenarios?.find((scenario) => scenario.id === scenarioId) ?? scenarios?.[0], [scenarios, scenarioId]);
  const activeScenarioId = scenarioId || selectedScenario?.id || "";

  useEffect(() => {
    if (selectedScenario && !scenarioId) {
      setScenarioId(selectedScenario.id);
    }
  }, [scenarioId, selectedScenario]);

  useEffect(() => {
    if (benchmarks && benchmarks.length > 0 && !latestRun) {
      setLatestRun(benchmarks[0]);
    }
  }, [benchmarks, latestRun]);

  const strategyResults = (latestRun?.results?.strategy_results as Array<any> | undefined) ?? [];
  const scatterData = strategyResults.map((item) => ({
    x: item.compiled_metrics.depth,
    y: Number(((item.output_quality.approximation_ratio ?? 0) * 100).toFixed(1)),
    label: item.strategy_label ?? item.strategy?.label ?? item.strategy_key,
    environment: item.environment,
    gates: item.compiled_metrics.total_gates,
    twoQ: item.compiled_metrics.two_qubit_gate_count,
    success: Number(((item.output_quality.success_probability ?? 0) * 100).toFixed(1)),
  }));

  async function execute() {
    if (!activeScenarioId) return;
    setRunning(true);
    setMessage(null);
    try {
      const response = await api.runBenchmark({ scenario_id: activeScenarioId });
      setLatestRun(response);
      setMessage({
        tone: "success",
        title: "Benchmark complete",
        description: response.summary?.recommendation ?? "Compiled benchmark results are available.",
      });
      await reloadBenchmarks();
    } catch (err) {
      setMessage({
        tone: "error",
        title: "Benchmark failed",
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  if (scenariosLoading || integrationsLoading || benchmarksLoading) return <LoadingState label="Loading benchmark workspace..." />;
  if (scenariosError || !scenarios || !integrations || !benchmarks) {
    return <EmptyState title="Benchmark workspace unavailable" description={scenariosError ?? "Could not load benchmark data."} />;
  }

  const workload = latestRun?.results?.workload;
  const strategies = (latestRun?.results?.strategies as Array<any> | undefined) ?? [];
  const environments = (latestRun?.results?.executed_environments as string[] | undefined) ?? (latestRun?.results?.environments as string[] | undefined) ?? [];
  const environmentSummary = latestRun?.results?.environment_summary ?? {};

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 5 - Benchmarks"
        title="Benchmark integrity"
        description="Study how the reduced wildfire intervention QAOA workload survives qBraid-centered compilation across strategies and execution environments."
        actions={
          <button onClick={() => void execute()} disabled={!activeScenarioId || running} className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate disabled:opacity-50">
            {running ? "Running benchmark..." : "Run benchmark"}
          </button>
        }
      />

      <SimulatorBanner simulatorOnly={integrations.simulator_only} qbraidReady={integrations.qbraid_ready} />
      {message ? <Notice tone={message.tone} title={message.title} description={message.description} /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <SectionPanel>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Scenario</label>
                <select value={activeScenarioId} onChange={(event) => setScenarioId(event.target.value)} className="min-w-[320px] border border-border bg-card px-4 py-2.5 text-[13px] outline-none focus:border-primary transition-colors">
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusPill label={integrations.qbraid_ready ? "qBraid ready" : "qBraid degraded"} tone={integrations.qbraid_ready ? "good" : "warn"} />
                <StatusPill label={integrations.hardware_available ? "IBM ready" : "Simulator-only"} tone={integrations.hardware_available ? "good" : "warn"} />
              </div>
            </div>
          </SectionPanel>

          {latestRun ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <MetricTile label="Algorithm" value={latestRun.summary?.algorithm ?? workload?.algorithm ?? "QAOA"} hint={workload?.source_representation ?? latestRun.summary?.source_representation ?? "qiskit.QuantumCircuit"} />
                <MetricTile label="Best tradeoff" value={latestRun.summary?.best_strategy_label ?? latestRun.summary?.best_strategy ?? "n/a"} hint={latestRun.summary?.best_environment ?? "No best environment recorded"} />
                <MetricTile label="Conclusion" value={latestRun.status} hint={latestRun.summary?.recommendation ?? "No conclusion available"} />
              </div>

              {workload ? (
                <SectionPanel title="Benchmark study design" subtitle="What is being benchmarked and why it matters to wildfire planning">
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <MetricTile label="Workload" value={workload.algorithm ?? "QAOA"} hint={workload.name ?? "Reduced intervention workload"} />
                    <MetricTile label="Source representation" value={workload.source_representation ?? "qiskit.QuantumCircuit"} hint="Framework-level source before qBraid transformation" />
                    <MetricTile label="Strategies" value={String(strategies.length)} hint={strategies.map((item) => item.intermediate_representation).join(" vs ")} />
                    <MetricTile label="Environments" value={String(environments.length)} hint={environments.join(", ")} />
                  </div>
                  <p className="mt-5 border-t border-border pt-4 text-[13px] leading-relaxed text-muted-foreground">{workload.wildfire_relevance}</p>
                </SectionPanel>
              ) : null}

              {strategies.length > 0 ? (
                <SectionPanel title="Compared qBraid strategies" subtitle="The benchmark compares distinct qBraid transformation and target-preparation choices">
                  <div className="grid gap-4 lg:grid-cols-2">
                    {strategies.map((strategy) => (
                      <div key={strategy.id} className="border border-border bg-card p-5 border-l-2 border-l-qp-cyan">
                        <p className="text-[14px] font-bold text-foreground mb-2">{strategy.label}</p>
                        <p className="text-[13px] leading-relaxed text-muted-foreground">{strategy.description}</p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          <StatusPill label={strategy.intermediate_representation} tone="accent" />
                          <StatusPill label={strategy.compile_profile} tone="neutral" />
                          <StatusPill label={strategy.coupling_profile} tone="neutral" />
                        </div>
                      </div>
                    ))}
                  </div>
                </SectionPanel>
              ) : null}

              <SectionPanel title="Quality vs cost" subtitle="Lower depth is cheaper, higher approximation ratio is better, and marker size reflects total gate count.">
                {latestRun.status === "complete" && scatterData.length > 0 ? (
                  <div className="space-y-4">
                    <div className="h-[320px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 12, right: 24, bottom: 28, left: 12 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                          <XAxis dataKey="x" name="Compiled depth" tick={{ fontSize: 11 }} label={{ value: "Compiled depth", position: "bottom", fontSize: 11, fill: "#636882" }} />
                          <YAxis dataKey="y" name="Approximation ratio (%)" tick={{ fontSize: 11 }} label={{ value: "Approx. ratio (%)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#636882" }} />
                          <ZAxis dataKey="gates" range={[60, 220]} name="Total gates" />
                          <Tooltip
                            cursor={{ strokeDasharray: "4 4" }}
                            content={({ active, payload }) => {
                              if (!active || !payload?.[0]) return null;
                              const d = payload[0].payload;
                              return (
                                <div className="border border-border bg-card p-4 text-[12px] shadow-sm">
                                  <p className="font-bold text-foreground mb-1">{d.label}</p>
                                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">{d.environment}</p>
                                  <p className="mt-1 flex justify-between gap-4"><span>Depth:</span> <span className="font-mono text-foreground">{d.x}</span></p>
                                  <p className="flex justify-between gap-4"><span>Approx. ratio:</span> <span className="font-mono text-foreground">{d.y}%</span></p>
                                  <p className="mt-1 flex justify-between gap-4"><span>Total gates:</span> <span className="font-mono text-foreground">{d.gates}</span></p>
                                  <p className="flex justify-between gap-4"><span>2Q gates:</span> <span className="font-mono text-foreground">{d.twoQ}</span></p>
                                  <p className="mt-1 flex justify-between gap-4"><span>Success prob:</span> <span className="font-mono text-foreground">{d.success}%</span></p>
                                </div>
                              );
                            }}
                          />
                          <Scatter data={scatterData} fill="#06b6d4" />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="overflow-hidden border border-border bg-card">
                      <table className="w-full text-[12px]">
                        <thead className="bg-secondary/50 text-left text-[11px] uppercase tracking-[0.15em] font-bold text-muted-foreground border-b border-border">
                          <tr>
                            <th className="px-4 py-3">Strategy</th>
                            <th className="px-4 py-3">Environment</th>
                            <th className="px-4 py-3 text-right">Depth</th>
                            <th className="px-4 py-3 text-right">2Q</th>
                            <th className="px-4 py-3 text-right">Total</th>
                            <th className="px-4 py-3 text-right">Approx.</th>
                            <th className="px-4 py-3 text-right">Success</th>
                          </tr>
                        </thead>
                        <tbody>
                          {strategyResults.map((item, index) => (
                            <tr key={`${item.strategy_key}-${item.environment}-${index}`} className="border-t border-border">
                              <td className="px-4 py-3 font-medium">{item.strategy_label ?? item.strategy?.label ?? item.strategy_key}</td>
                              <td className="px-4 py-3 text-muted-foreground">{item.environment}</td>
                              <td className="px-4 py-3 text-right font-mono">{item.compiled_metrics.depth}</td>
                              <td className="px-4 py-3 text-right font-mono">{item.compiled_metrics.two_qubit_gate_count}</td>
                              <td className="px-4 py-3 text-right font-mono">{item.compiled_metrics.total_gates}</td>
                              <td className="px-4 py-3 text-right font-mono">{`${(item.output_quality.approximation_ratio * 100).toFixed(1)}%`}</td>
                              <td className="px-4 py-3 text-right font-mono">{`${(item.output_quality.success_probability * 100).toFixed(1)}%`}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <Notice tone="warn" title="Compiled benchmark results unavailable" description={latestRun.results?.note ?? "This run did not produce a complete strategy comparison."} />
                )}
              </SectionPanel>

              {Object.keys(environmentSummary).length > 0 ? (
                <SectionPanel title="Environment-by-environment outcome" subtitle="This is where the benchmark decides which strategy held up best under each execution context">
                  <div className="grid gap-4 lg:grid-cols-3">
                    {Object.entries(environmentSummary).map(([environment, summary]) => (
                      <div key={environment} className="border border-border bg-card p-5">
                        <p className="text-[13px] font-bold uppercase tracking-wider text-foreground mb-3 border-b border-border pb-2">{environment}</p>
                        <p className="mt-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Quality leader</p>
                        <p className="text-[14px] font-medium text-foreground">{String((summary as any).quality_winner?.strategy_label ?? "n/a")}</p>
                        <p className="mt-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Cost leader</p>
                        <p className="text-[14px] font-medium text-foreground">{String((summary as any).cost_winner?.strategy_label ?? "n/a")}</p>
                        <p className="mt-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Best tradeoff</p>
                        <p className="text-[14px] font-medium text-foreground">{String((summary as any).tradeoff_winner?.strategy_label ?? "n/a")}</p>
                      </div>
                    ))}
                  </div>
                </SectionPanel>
              ) : null}

              <SectionPanel title="Continue workflow" subtitle="Use this run in reporting or inspect the full benchmark detail.">
                <div className="flex flex-wrap gap-2">
                  <Link to={`/app/benchmarks/${latestRun.id}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Open detail
                  </Link>
                  <Link to={`/app/reports?scenario=${activeScenarioId}&benchmark=${latestRun.id}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Report with this run
                  </Link>
                </div>
              </SectionPanel>
            </>
          ) : (
            <EmptyState
              title="No benchmark evidence yet"
              description="Run benchmark integrity to compare qBraid compilation strategies, execution environments, and the cost of preserving useful optimization behavior."
            />
          )}
        </div>

        <SectionPanel title="Benchmark history" subtitle="Saved benchmark evidence for this scenario">
          <div className="space-y-3">
            {benchmarks.length === 0 ? (
              <p className="text-[12px] text-muted-foreground">No benchmark runs saved for this scenario yet.</p>
            ) : (
              benchmarks.slice(0, 10).map((run) => (
                <button
                  key={run.id}
                  onClick={() => setLatestRun(run)}
                  className={`w-full border p-4 text-left transition-colors ${latestRun?.id === run.id ? "border-primary bg-secondary/30" : "border-border bg-card hover:border-primary/50"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[13px] font-bold">{run.id.slice(0, 8)}</p>
                      <p className="mt-1 text-[11px] text-muted-foreground">{new Date(run.created_at).toLocaleString()}</p>
                    </div>
                    <StatusPill label={run.status} tone={run.status === "complete" ? "good" : "warn"} />
                  </div>
                </button>
              ))
            )}
          </div>
        </SectionPanel>
      </div>
    </div>
  );
}
