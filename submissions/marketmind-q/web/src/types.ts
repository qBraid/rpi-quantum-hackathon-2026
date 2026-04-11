export type TabId = "boundary" | "arena" | "qbraid" | "tour";

export interface MetricRow {
  model: string;
  modelFamily: string;
  executionMode: string;
  trainSize: number;
  featureDim: number | null;
  splitId: string;
  cutoffDate: string;
  balancedAccuracy: number;
  f1: number;
  rocAuc: number;
  precisionTopDecile: number;
  signalReturnMean: number;
  signalSharpe: number;
  maxDrawdown: number;
  trainSeconds: number;
  inferSeconds: number;
  qubits: number | null;
  kernelCircuitDepth: number | null;
  kernelTwoQubitGates: number | null;
  shots: number | null;
  selectedFeatures: string;
  marketRegime: string;
  confusionMatrix: string;
}

export interface QBraidMetricRow {
  pairId: string;
  pairKind: string;
  strategy: string;
  executionEnvironment: string;
  programType: string;
  sourcePZero: number | null;
  compiledPZero: number | null;
  absProbabilityError: number | null;
  hellingerDistance: number | null;
  qubits: number | null;
  depth: number | null;
  twoQubitGates: number | null;
  measurementCount: number | null;
  serializedSize: number | null;
  transpileSeconds: number | null;
  executionSeconds: number | null;
  shots: number | null;
  status: string;
  qbraidAllclose: string;
  selectedFeatures: string;
  sourceSplitId: string;
  sourceTrainSize: number | null;
  sourceFeatureDim: number | null;
  sourceRocAuc: number | null;
}

export interface QBraidPathRow {
  source: string;
  target: string;
  pathCount: number;
  paths: string;
  shortestPath: string;
  status: string;
  qbraidVersion: string;
}

export interface QmlEdgeRow {
  key: string;
  trainSize: number;
  featureDim: number;
  splitId: string;
  cutoffDate: string;
  marketRegime: string;
  selectedFeatures: string;
  qmlEdge: number;
  quantumRow: MetricRow;
  bestClassicalRow: MetricRow;
}

export interface HeatmapCell {
  key: string;
  trainSize: number;
  featureDim: number;
  meanEdge: number;
  bestEdge: number;
  count: number;
  representative: QmlEdgeRow;
}

export interface QBraidSummary {
  key: string;
  strategy: string;
  executionEnvironment: string;
  programType: string;
  rows: number;
  successes: number;
  meanAbsProbabilityError: number;
  maxAbsProbabilityError: number;
  meanHellingerDistance: number;
  meanDepth: number;
  meanTwoQubitGates: number;
  meanTranspileSeconds: number;
  meanExecutionSeconds: number;
  shots: number | null;
}

export interface DashboardData {
  metrics: MetricRow[];
  qbraidMetrics: QBraidMetricRow[];
  qbraidPaths: QBraidPathRow[];
  qmlEdges: QmlEdgeRow[];
  heatmapCells: HeatmapCell[];
  trainSizes: number[];
  featureDims: number[];
  qbraidSummary: QBraidSummary[];
}
