import Papa from "papaparse";
import type {
  DashboardData,
  HeatmapCell,
  MetricRow,
  QBraidMetricRow,
  QBraidPathRow,
  QBraidSummary,
  QmlEdgeRow,
} from "./types";

type CsvRecord = Record<string, string | undefined>;

const missingMessage = [
  "Missing dashboard artifacts.",
  "Run `python -m src.run_benchmark --config configs/sector_etf.yaml`,",
  "`python -m src.qbraid_benchmark --config configs/qbraid.yaml`,",
  "then `npm run sync-data` inside `web/`.",
].join(" ");

function publicPath(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`;
}

function toNumber(value: string | undefined): number | null {
  if (value === undefined || value === "" || value.toLowerCase() === "nan") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function requiredNumber(value: string | undefined, fallback = 0): number {
  return toNumber(value) ?? fallback;
}

async function parseCsv<T>(path: string, mapper: (record: CsvRecord) => T): Promise<T[]> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${missingMessage} Could not load ${path}.`);
  }
  const text = await response.text();
  const parsed = Papa.parse<CsvRecord>(text, {
    header: true,
    skipEmptyLines: true,
  });
  if (parsed.errors.length > 0) {
    throw new Error(`Could not parse ${path}: ${parsed.errors[0].message}`);
  }
  return parsed.data.map(mapper);
}

function mapMetric(record: CsvRecord): MetricRow {
  return {
    model: record.model ?? "",
    modelFamily: record.model_family ?? "",
    executionMode: record.execution_mode ?? "",
    trainSize: requiredNumber(record.train_size),
    featureDim: toNumber(record.feature_dim),
    splitId: record.split_id ?? "",
    cutoffDate: record.cutoff_date ?? "",
    balancedAccuracy: requiredNumber(record.balanced_accuracy),
    f1: requiredNumber(record.f1),
    rocAuc: requiredNumber(record.roc_auc),
    precisionTopDecile: requiredNumber(record.precision_top_decile),
    signalReturnMean: requiredNumber(record.signal_return_mean),
    signalSharpe: requiredNumber(record.signal_sharpe),
    maxDrawdown: requiredNumber(record.max_drawdown),
    trainSeconds: requiredNumber(record.train_seconds),
    inferSeconds: requiredNumber(record.infer_seconds),
    qubits: toNumber(record.qubits),
    kernelCircuitDepth: toNumber(record.kernel_circuit_depth),
    kernelTwoQubitGates: toNumber(record.kernel_two_qubit_gates),
    shots: toNumber(record.shots),
    selectedFeatures: record.selected_features && record.selected_features !== "nan" ? record.selected_features : "",
    marketRegime: record.market_regime ?? "",
    confusionMatrix: record.confusion_matrix ?? "",
  };
}

function mapQBraidMetric(record: CsvRecord): QBraidMetricRow {
  return {
    pairId: record.pair_id ?? "",
    pairKind: record.pair_kind ?? "",
    strategy: record.strategy ?? "",
    executionEnvironment: record.execution_environment ?? "",
    programType: record.program_type ?? "",
    sourcePZero: toNumber(record.source_p_zero),
    compiledPZero: toNumber(record.compiled_p_zero),
    absProbabilityError: toNumber(record.abs_probability_error),
    hellingerDistance: toNumber(record.hellinger_distance),
    qubits: toNumber(record.qubits),
    depth: toNumber(record.depth),
    twoQubitGates: toNumber(record.two_qubit_gates),
    measurementCount: toNumber(record.measurement_count),
    serializedSize: toNumber(record.serialized_size),
    transpileSeconds: toNumber(record.transpile_seconds),
    executionSeconds: toNumber(record.execution_seconds),
    shots: toNumber(record.shots),
    status: record.status ?? "",
    qbraidAllclose: record.qbraid_allclose ?? "",
    selectedFeatures: record.selected_features ?? "",
    sourceSplitId: record.source_split_id ?? "",
    sourceTrainSize: toNumber(record.source_train_size),
    sourceFeatureDim: toNumber(record.source_feature_dim),
    sourceRocAuc: toNumber(record.source_roc_auc),
  };
}

function mapQBraidPath(record: CsvRecord): QBraidPathRow {
  return {
    source: record.source ?? "",
    target: record.target ?? "",
    pathCount: requiredNumber(record.path_count),
    paths: record.paths ?? "",
    shortestPath: record.shortest_path ?? "",
    status: record.status ?? "",
    qbraidVersion: record.qbraid_version ?? "",
  };
}

function bestBy<T>(rows: T[], score: (row: T) => number): T | undefined {
  return rows.reduce<T | undefined>((best, row) => {
    if (!best || score(row) > score(best)) {
      return row;
    }
    return best;
  }, undefined);
}

function deriveQmlEdges(metrics: MetricRow[]): QmlEdgeRow[] {
  const bestClassicalBySplit = new Map<string, MetricRow>();
  for (const row of metrics) {
    if (row.modelFamily !== "classical") {
      continue;
    }
    const key = `${row.trainSize}:${row.splitId}`;
    const current = bestClassicalBySplit.get(key);
    if (!current || row.rocAuc > current.rocAuc) {
      bestClassicalBySplit.set(key, row);
    }
  }

  return metrics
    .filter(
      (row) =>
        row.model === "quantum_kernel_svm" &&
        row.modelFamily === "quantum" &&
        row.executionMode === "statevector_exact" &&
        row.featureDim !== null,
    )
    .flatMap((quantumRow) => {
      const bestClassicalRow = bestClassicalBySplit.get(`${quantumRow.trainSize}:${quantumRow.splitId}`);
      if (!bestClassicalRow || quantumRow.featureDim === null) {
        return [];
      }
      return [
        {
          key: `${quantumRow.trainSize}:${quantumRow.featureDim}:${quantumRow.splitId}`,
          trainSize: quantumRow.trainSize,
          featureDim: quantumRow.featureDim,
          splitId: quantumRow.splitId,
          cutoffDate: quantumRow.cutoffDate,
          marketRegime: quantumRow.marketRegime,
          selectedFeatures: quantumRow.selectedFeatures,
          qmlEdge: quantumRow.rocAuc - bestClassicalRow.rocAuc,
          quantumRow,
          bestClassicalRow,
        },
      ];
    });
}

function deriveHeatmap(qmlEdges: QmlEdgeRow[]): HeatmapCell[] {
  const groups = new Map<string, QmlEdgeRow[]>();
  for (const edge of qmlEdges) {
    const key = `${edge.trainSize}:${edge.featureDim}`;
    groups.set(key, [...(groups.get(key) ?? []), edge]);
  }

  return Array.from(groups.entries()).map(([key, rows]) => {
    const representative = bestBy(rows, (row) => row.qmlEdge) ?? rows[0];
    const meanEdge = rows.reduce((sum, row) => sum + row.qmlEdge, 0) / rows.length;
    const bestEdge = Math.max(...rows.map((row) => row.qmlEdge));
    return {
      key,
      trainSize: representative.trainSize,
      featureDim: representative.featureDim,
      meanEdge,
      bestEdge,
      count: rows.length,
      representative,
    };
  });
}

function mean(values: Array<number | null>): number {
  const usable = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (usable.length === 0) {
    return 0;
  }
  return usable.reduce((sum, value) => sum + value, 0) / usable.length;
}

function deriveQBraidSummary(rows: QBraidMetricRow[]): QBraidSummary[] {
  const groups = new Map<string, QBraidMetricRow[]>();
  for (const row of rows) {
    const key = `${row.strategy}:${row.executionEnvironment}:${row.programType}`;
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }

  return Array.from(groups.entries()).map(([key, group]) => ({
    key,
    strategy: group[0].strategy,
    executionEnvironment: group[0].executionEnvironment,
    programType: group[0].programType,
    rows: group.length,
    successes: group.filter((row) => row.status === "success").length,
    meanAbsProbabilityError: mean(group.map((row) => row.absProbabilityError)),
    maxAbsProbabilityError: Math.max(...group.map((row) => row.absProbabilityError ?? 0)),
    meanHellingerDistance: mean(group.map((row) => row.hellingerDistance)),
    meanDepth: mean(group.map((row) => row.depth)),
    meanTwoQubitGates: mean(group.map((row) => row.twoQubitGates)),
    meanTranspileSeconds: mean(group.map((row) => row.transpileSeconds)),
    meanExecutionSeconds: mean(group.map((row) => row.executionSeconds)),
    shots: group.find((row) => row.shots !== null)?.shots ?? null,
  }));
}

export async function loadDashboardData(): Promise<DashboardData> {
  const [metrics, qbraidMetrics, qbraidPaths] = await Promise.all([
    parseCsv(publicPath("data/metrics_summary.csv"), mapMetric),
    parseCsv(publicPath("data/qbraid_compile_metrics.csv"), mapQBraidMetric),
    parseCsv(publicPath("data/qbraid_path_summary.csv"), mapQBraidPath),
  ]);
  const qmlEdges = deriveQmlEdges(metrics);
  const heatmapCells = deriveHeatmap(qmlEdges);
  return {
    metrics,
    qbraidMetrics,
    qbraidPaths,
    qmlEdges,
    heatmapCells,
    trainSizes: Array.from(new Set(heatmapCells.map((cell) => cell.trainSize))).sort((a, b) => a - b),
    featureDims: Array.from(new Set(heatmapCells.map((cell) => cell.featureDim))).sort((a, b) => a - b),
    qbraidSummary: deriveQBraidSummary(qbraidMetrics),
  };
}
