export type CellState =
  | "empty"
  | "road_or_firebreak"
  | "dry_brush"
  | "grass"
  | "shrub"
  | "tree"
  | "water"
  | "protected"
  | "intervention"
  | "ignition"
  | "burned";

export type Scenario = {
  id: string;
  name: string;
  domain: string;
  status: string;
  description: string;
  version: number;
  archived: boolean;
  grid: CellState[][];
  metadata_json: Record<string, unknown>;
  constraints_json: Record<string, unknown>;
  objectives_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ScenarioPayload = {
  name: string;
  domain: string;
  status: string;
  description: string;
  grid: CellState[][];
  metadata_json: Record<string, unknown>;
  constraints_json: Record<string, unknown>;
  objectives_json: Record<string, unknown>;
};

export type RiskRun = {
  id: string;
  scenario_id: string;
  scenario_version: number;
  status: string;
  modes: string[];
  request: Record<string, unknown>;
  results: Record<string, any>;
  summary: Record<string, any>;
  created_at: string;
};

export type ForecastRun = {
  id: string;
  scenario_id: string;
  scenario_version: number;
  status: string;
  request: Record<string, unknown>;
  snapshots: Array<Record<string, any>>;
  summary: Record<string, any>;
  diagnostics: Record<string, any>;
  created_at: string;
};

export type OptimizationRun = {
  id: string;
  scenario_id: string;
  scenario_version: number;
  status: string;
  request: Record<string, unknown>;
  results: Record<string, any>;
  summary: Record<string, any>;
  created_at: string;
};

export type BenchmarkRun = {
  id: string;
  scenario_id: string;
  scenario_version: number;
  optimization_run_id?: string | null;
  status: string;
  request: Record<string, unknown>;
  results: Record<string, any>;
  summary: Record<string, any>;
  availability: Record<string, any>;
  created_at: string;
};

export type ReportRecord = {
  id: string;
  scenario_id: string;
  title: string;
  status: string;
  sections: Record<string, any>;
  export: Record<string, any>;
  created_at: string;
};

export type IntegrationProvider = {
  provider: string;
  available: boolean;
  mode: string;
  details: Record<string, any>;
  updated_at: string;
};

export type IntegrationSummary = {
  simulator_only: boolean;
  hardware_available: boolean;
  qbraid_ready: boolean;
  providers: IntegrationProvider[];
};

export type OverviewData = {
  portfolio: Record<string, any>;
  recent: Record<string, any>;
  system: Record<string, any>;
};
