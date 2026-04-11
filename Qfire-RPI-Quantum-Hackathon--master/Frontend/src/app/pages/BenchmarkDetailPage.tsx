import { Link, useParams } from "react-router";
import { ChevronLeft } from "lucide-react";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, Notice, PageHeader, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

export function BenchmarkDetailPage() {
  const { id = "" } = useParams();
  const { data: run, loading, error } = useAsyncData(() => api.getBenchmark(id), [id]);

  if (loading) return <LoadingState label="Loading benchmark detail..." />;
  if (error || !run) return <EmptyState title="Benchmark run unavailable" description={error ?? "Run not found."} />;

  const workload = run.results?.workload;
  const strategies = (run.results?.strategies as Array<any> | undefined) ?? [];
  const strategyResults = (run.results?.strategy_results as Array<any> | undefined) ?? [];
  const environmentSummary = run.results?.environment_summary ?? {};
  const firstResultByStrategy = new Map<string, any>();
  for (const result of strategyResults) {
    if (!firstResultByStrategy.has(result.strategy_key)) {
      firstResultByStrategy.set(result.strategy_key, result);
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/app/benchmarks" className="inline-flex items-center gap-2 text-[13px] text-muted-foreground hover:text-foreground">
        <ChevronLeft className="h-4 w-4" /> Back to benchmarks
      </Link>

      <PageHeader
        eyebrow="Benchmark detail"
        title="Benchmark integrity run"
        description={run.summary?.recommendation ?? "Inspect the workload, qBraid transformations, execution environments, and the quality-cost tradeoff."}
      />

      <SectionPanel>
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill label={run.status} tone={run.status === "complete" ? "good" : "warn"} />
          <StatusPill label={run.availability?.mode ?? "unknown"} tone={run.availability?.mode === "ready" ? "good" : "warn"} />
          {run.summary?.algorithm ? <StatusPill label={run.summary.algorithm} tone="accent" /> : null}
          {run.summary?.source_representation ? <StatusPill label={run.summary.source_representation} /> : null}
          {run.summary?.qiskit_version ? <StatusPill label={`Qiskit ${run.summary.qiskit_version}`} /> : null}
          {run.summary?.qbraid_version ? <StatusPill label={`qBraid ${run.summary.qbraid_version}`} /> : null}
        </div>
      </SectionPanel>

      {run.status !== "complete" ? (
        <Notice
          tone="warn"
          title={run.status === "degraded" ? "Degraded benchmark" : "Benchmark error"}
          description={run.results?.note ?? "This benchmark did not produce full compiled results."}
        />
      ) : null}

      {workload ? (
        <SectionPanel title="What algorithm was run?" subtitle="This section makes the workload and its product relevance explicit">
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
            <MetricTile label="Algorithm" value={workload.algorithm ?? "QAOA"} />
            <MetricTile label="Source framework" value={workload.source_representation ?? "qiskit.QuantumCircuit"} />
            <MetricTile label="Qubits" value={String(workload.problem_size?.num_qubits ?? workload.uncompiled_circuit?.width ?? "n/a")} />
            <MetricTile label="Raw depth" value={String(workload.uncompiled_circuit?.depth ?? "n/a")} />
            <MetricTile label="Raw 2Q gates" value={String(workload.uncompiled_circuit?.two_qubit_gate_count ?? "n/a")} />
            <MetricTile label="Exact best cost" value={String(workload.exact_reference?.best_cost ?? "n/a")} />
          </div>
          <div className="mt-4 space-y-3 text-[13px] leading-6 text-muted-foreground">
            <p>{workload.objective}</p>
            <p>{workload.wildfire_relevance}</p>
            <p>{workload.benchmark_question}</p>
          </div>
        </SectionPanel>
      ) : null}

      {strategies.length > 0 ? (
        <SectionPanel title="How did qBraid transform it?" subtitle="Each strategy changes the intermediate representation and target-preparation profile">
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
                {firstResultByStrategy.get(strategy.id)?.strategy?.qbraid_transform ? (
                  <div className="mt-5 border-t border-border pt-4 text-[12px] leading-relaxed text-muted-foreground">
                    <p className="font-bold uppercase tracking-wider text-foreground mb-2 text-[11px]">qBraid conversion path</p>
                    <p><span className="font-semibold text-foreground">Forward:</span> {(firstResultByStrategy.get(strategy.id).strategy.qbraid_transform.forward_path ?? []).join(" -> ")}</p>
                    <p className="mt-1"><span className="font-semibold text-foreground">Reverse:</span> {(firstResultByStrategy.get(strategy.id).strategy.qbraid_transform.reverse_path ?? []).join(" -> ")}</p>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </SectionPanel>
      ) : null}

      {Object.keys(environmentSummary).length > 0 ? (
        <SectionPanel title="Which preserved useful performance best?" subtitle="Environment summaries compare quality winners, cost winners, and best tradeoff winners">
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

      {strategyResults.length > 0 ? (
        <SectionPanel title="What was the cost in compiled resources?" subtitle="Every row combines qBraid strategy, execution environment, output quality, and compiled cost">
          <div className="overflow-hidden border border-border bg-card">
            <table className="w-full text-[12px]">
              <thead className="bg-secondary/50 border-b border-border">
                <tr className="text-left text-[11px] font-bold uppercase tracking-[0.15em] text-muted-foreground">
                  <th className="px-4 py-3">Strategy</th>
                  <th className="px-4 py-3">Intermediate</th>
                  <th className="px-4 py-3">Environment</th>
                  <th className="px-4 py-3 text-right">Depth</th>
                  <th className="px-4 py-3 text-right">2Q gates</th>
                  <th className="px-4 py-3 text-right">Total gates</th>
                  <th className="px-4 py-3 text-right">Approx.</th>
                  <th className="px-4 py-3 text-right">Success</th>
                </tr>
              </thead>
              <tbody>
                {strategyResults.map((result: any, idx: number) => {
                  const isBest = result.strategy_key === run.summary?.best_strategy && result.environment === run.summary?.best_environment;
                  return (
                    <tr key={idx} className={`border-t border-border ${isBest ? "bg-cyan-50/50" : ""}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{result.strategy_label ?? result.strategy?.label ?? result.strategy_key}</span>
                          {isBest ? <StatusPill label="Best" tone="good" /> : null}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{result.strategy?.intermediate_representation ?? "-"}</td>
                      <td className="px-4 py-3 text-muted-foreground">{result.environment}</td>
                      <td className="px-4 py-3 text-right font-mono">{result.compiled_metrics?.depth ?? "-"}</td>
                      <td className="px-4 py-3 text-right font-mono">{result.compiled_metrics?.two_qubit_gate_count ?? "-"}</td>
                      <td className="px-4 py-3 text-right font-mono">{result.compiled_metrics?.total_gates ?? "-"}</td>
                      <td className="px-4 py-3 text-right font-mono">
                        {result.output_quality?.approximation_ratio != null ? `${(result.output_quality.approximation_ratio * 100).toFixed(1)}%` : "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {result.output_quality?.success_probability != null ? `${(result.output_quality.success_probability * 100).toFixed(1)}%` : "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionPanel>
      ) : null}

      {strategyResults.some((item: any) => item.artifacts?.job_id) ? (
        <SectionPanel title="Hardware artifacts" subtitle="IBM Runtime metadata is shown only when hardware execution actually occurred">
          <div className="grid gap-4 lg:grid-cols-2">
            {strategyResults
              .filter((item: any) => item.artifacts?.job_id)
              .map((item: any) => (
                <div key={`${item.strategy_key}-${item.environment}`} className="border border-border bg-card p-5">
                  <p className="text-[14px] font-bold text-foreground mb-2">{item.strategy_label}</p>
                  <p className="text-[13px] leading-relaxed text-muted-foreground"><span className="font-semibold text-foreground">Backend:</span> {item.execution_notes?.target_backend ?? "n/a"}</p>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground"><span className="font-semibold text-foreground">Job ID:</span> {item.artifacts?.job_id}</p>
                </div>
              ))}
          </div>
        </SectionPanel>
      ) : null}

      <SectionPanel title="Continue workflow" subtitle="Use this benchmark record as evidence in the final wildfire planning report.">
        <div className="flex flex-wrap gap-2">
          <Link to={`/app/reports?scenario=${run.scenario_id}&benchmark=${run.id}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
            Report with this run
          </Link>
        </div>
      </SectionPanel>
    </div>
  );
}
