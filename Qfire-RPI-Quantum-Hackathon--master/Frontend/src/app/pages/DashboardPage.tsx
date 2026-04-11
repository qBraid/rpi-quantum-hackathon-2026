import { Link } from "react-router";
import { ArrowRight, Cpu, FileText, Flame, Layers, Target, TrendingUp } from "lucide-react";

import { api } from "../api";
import { EmptyState, LoadingState, MetricTile, PageHeader, SectionPanel, StatusPill } from "../components/product";
import { useAsyncData } from "../useAsyncData";

export function DashboardPage() {
  const { data, loading, error, reload } = useAsyncData(
    async () => {
      const [overview, scenarios, benchmarks, integrations] = await Promise.all([
        api.overview(),
        api.listScenarios(),
        api.listBenchmarks(),
        api.integrations(),
      ]);
      return { overview, scenarios, benchmarks, integrations };
    },
    [],
  );

  if (loading) return <LoadingState label="Loading overview..." />;
  if (error || !data) {
    return (
      <EmptyState
        title="Overview unavailable"
        description={error ?? "The dashboard could not be loaded."}
        action={
          <button onClick={() => void reload()} className="bg-primary px-6 py-2.5 text-[12px] font-bold uppercase tracking-wider text-primary-foreground">
            Retry
          </button>
        }
      />
    );
  }

  const { overview, scenarios, benchmarks, integrations } = data;
  const activeScenarios = scenarios.filter((scenario) => scenario.status === "active").length;
  const degradedBenchmarks = benchmarks.filter((run) => run.status !== "complete").length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Command center"
        title="Wildfire planning command center"
        description="A pre-season spatial decision intelligence platform. It sequences structural-risk modeling, forecast ensembles, and resource allocation alongside real quantum benchmark studies."
        actions={
          <Link to="/app/scenarios/new" className="inline-flex items-center justify-center bg-primary px-6 py-3 text-[13px] font-bold uppercase tracking-wider text-primary-foreground transition-all hover:bg-qp-slate">
            New scenario
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Scenarios" value={String(overview.portfolio.scenario_count)} hint={`${activeScenarios} active hillside planning cases`} />
        <MetricTile label="Risk maps" value={String(overview.portfolio.risk_runs)} hint="Saved classical, quantum, and hybrid comparisons" />
        <MetricTile label="Benchmark evidence" value={String(overview.portfolio.benchmark_runs)} hint={`${degradedBenchmarks} runs still missing full compiler or hardware support`} />
        <MetricTile label="Reports" value={String(overview.portfolio.report_count)} hint="Planner-facing decision packets ready to export" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <SectionPanel
          title="The Decision Workflow"
          subtitle="How QuantumProj combines wildfire modeling with quantum compilation tradeoffs."
        >
          <div className="grid gap-4 md:grid-cols-3 h-full">
            {[
              { icon: Layers, title: "1. Scenario Setup", text: "Create a 10x10 wildfire grid with structural terrain and intervention budget.", href: "/app/scenarios" },
              { icon: TrendingUp, title: "2. Analysis", text: "Map stochastic burn risks and predict spread corridors using a unified science core.", href: "/app/risk" },
              { icon: Target, title: "3. Mitigation & QA", text: "Target interventions, then compile workloads across environments via qBraid for integrity validation.", href: "/app/optimize" },
            ].map((item) => (
              <Link key={item.title} to={item.href} className="group relative flex flex-col justify-between overflow-hidden border border-border bg-card p-5 transition-all hover:border-primary/60">
                <div>
                  <item.icon className="mb-4 h-6 w-6 text-primary transition-transform group-hover:scale-110" />
                  <h3 className="text-[15px] font-bold text-foreground">{item.title}</h3>
                  <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">{item.text}</p>
                </div>
              </Link>
            ))}
          </div>
        </SectionPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2 mt-8">
        <SectionPanel title="Active planning constraints" subtitle="The current workspace environment settings.">
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground border-b border-border pb-2 mb-3">Benchmark integrity</p>
              <div className="flex items-center justify-between">
                <p className="text-[14px] font-semibold text-foreground">qBraid-centered pipeline</p>
                <StatusPill label={integrations.qbraid_ready ? "SDK detected" : "Degraded"} tone={integrations.qbraid_ready ? "good" : "warn"} />
              </div>
              <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
                {integrations.qbraid_ready
                  ? "Compiler-aware benchmarking can execute natively."
                  : "Benchmark evidence stays explicitly degraded until qBraid and Qiskit are installed."}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground border-b border-border pb-2 mb-3">Execution environments</p>
              <div className="flex flex-wrap gap-2">
                <StatusPill label="Ideal simulator" tone="good" />
                <StatusPill label="Noisy simulator" tone="accent" />
                <StatusPill label={integrations.hardware_available ? "IBM hardware configured" : "IBM hardware unavailable"} tone={integrations.hardware_available ? "good" : "warn"} />
              </div>
            </div>
          </div>
        </SectionPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
        <SectionPanel title="Recent scenarios" subtitle="Open a hillside case to continue the planning workflow from the exact saved version.">
          <div className="space-y-3">
            {scenarios.slice(0, 5).map((scenario) => (
              <Link
                key={scenario.id}
                to={`/app/scenarios/${scenario.id}`}
                className="flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4 transition-colors hover:border-primary/50"
              >
                <div className="flex items-start gap-4">
                  <div className="mt-1 flex h-8 w-8 items-center justify-center bg-qp-red/10 text-qp-red border border-qp-red/20">
                    <Flame className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[14px] font-bold text-foreground">{scenario.name}</p>
                    <p className="mt-1 text-[12px] font-medium uppercase tracking-wider text-muted-foreground">v{scenario.version} • {scenario.domain} • {scenario.status}</p>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
              </Link>
            ))}
          </div>
        </SectionPanel>

        <SectionPanel title="Recent benchmark and report activity" subtitle="Use this to check whether each scenario already has trust evidence and a reportable recommendation.">
          <div className="space-y-4">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Cpu className="h-4 w-4 text-qp-cyan" />
                <p className="text-[13px] font-semibold">Benchmarks</p>
              </div>
              <div className="space-y-2">
                {benchmarks.slice(0, 3).map((run) => (
                  <Link key={run.id} to={`/app/benchmarks/${run.id}`} className="flex items-center justify-between rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/50">
                    <div>
                      <p className="text-[13px] font-medium">{run.id}</p>
                      <p className="text-[12px] text-muted-foreground mt-1">{run.summary?.recommendation ?? "No recommendation available"}</p>
                    </div>
                    <StatusPill label={run.status} tone={run.status === "complete" ? "good" : "warn"} />
                  </Link>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4 text-qp-violet" />
                <p className="text-[13px] font-semibold">Reports</p>
              </div>
              <div className="space-y-2">
                {(overview.recent.reports as Array<{ id: string; title: string; created_at: string }>).slice(0, 3).map((report) => (
                  <div key={report.id} className="rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/50">
                    <p className="text-[13px] font-medium">{report.title}</p>
                    <p className="mt-1 text-[12px] text-muted-foreground">{new Date(report.created_at).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </SectionPanel>
      </div>
    </div>
  );
}
