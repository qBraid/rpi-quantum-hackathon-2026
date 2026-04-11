import type {
  BenchmarkRun,
  ForecastRun,
  IntegrationSummary,
  OptimizationRun,
  OverviewData,
  ReportRecord,
  RiskRun,
  Scenario,
  ScenarioPayload,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; app: string }>("/health"),
  overview: () => request<OverviewData>("/overview"),
  listScenarios: () => request<Scenario[]>("/scenarios"),
  getScenario: (id: string) => request<Scenario>(`/scenarios/${id}`),
  createScenario: (payload: ScenarioPayload) =>
    request<Scenario>("/scenarios", { method: "POST", body: JSON.stringify(payload) }),
  updateScenario: (id: string, payload: Partial<ScenarioPayload> & { archived?: boolean }) =>
    request<Scenario>(`/scenarios/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteScenario: (id: string) => request<{ message: string }>(`/scenarios/${id}`, { method: "DELETE" }),
  runRisk: (payload: { scenario_id: string; modes?: string[]; threshold?: number; horizon_steps?: number; sample_count?: number; seed?: number }) =>
    request<RiskRun>("/risk/run", { method: "POST", body: JSON.stringify(payload) }),
  listRiskRuns: (scenarioId?: string) =>
    request<RiskRun[]>(`/risk/runs${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  getRiskRun: (id: string) => request<RiskRun>(`/risk/runs/${id}`),
  runForecast: (payload: {
    scenario_id: string;
    steps?: number;
    dryness?: number;
    spread_sensitivity?: number;
    wind_speed?: number;
    slope_influence?: number;
    spotting_likelihood?: number;
    ensemble_runs?: number;
    seed?: number;
    wind_direction?: string;
  }) => request<ForecastRun>("/forecast/run", { method: "POST", body: JSON.stringify(payload) }),
  listForecastRuns: (scenarioId?: string) =>
    request<ForecastRun[]>(`/forecast/runs${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  getForecastRun: (id: string) => request<ForecastRun>(`/forecast/runs/${id}`),
  runOptimize: (payload: { scenario_id: string; mode?: "planning" | "challenge"; intervention_budget_k?: number; reduced_candidate_count?: number }) =>
    request<OptimizationRun>("/optimize/run", { method: "POST", body: JSON.stringify(payload) }),
  listOptimizeRuns: (scenarioId?: string) =>
    request<OptimizationRun[]>(`/optimize/runs${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  getOptimizeRun: (id: string) => request<OptimizationRun>(`/optimize/runs/${id}`),
  runBenchmark: (payload: {
    scenario_id: string;
    optimization_run_id?: string | null;
    shots?: number;
    reduced_candidate_count?: number;
    environments?: string[];
  }) => request<BenchmarkRun>("/benchmarks/run", { method: "POST", body: JSON.stringify(payload) }),
  listBenchmarks: (scenarioId?: string) =>
    request<BenchmarkRun[]>(`/benchmarks${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  getBenchmark: (id: string) => request<BenchmarkRun>(`/benchmarks/${id}`),
  generateReport: (payload: {
    scenario_id: string;
    risk_run_id?: string | null;
    forecast_run_id?: string | null;
    optimization_run_id?: string | null;
    benchmark_run_id?: string | null;
    title?: string;
  }) => request<ReportRecord>("/reports/generate", { method: "POST", body: JSON.stringify(payload) }),
  listReports: (scenarioId?: string) =>
    request<ReportRecord[]>(`/reports${scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ""}`),
  getReport: (id: string) => request<ReportRecord>(`/reports/${id}`),
  integrations: () => request<IntegrationSummary>("/integrations/status"),
};
