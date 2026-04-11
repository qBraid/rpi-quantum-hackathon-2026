import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardData, MetricRow, QmlEdgeRow } from "../types";
import { MetricTile } from "./MetricTile";

interface ModelArenaProps {
  data: DashboardData;
  selected: QmlEdgeRow;
}

function fmt(value: number, digits = 3): string {
  return value.toFixed(digits);
}

function modelLabel(row: MetricRow): string {
  if (row.modelFamily === "quantum") {
    return `${row.executionMode.replace("_", " ")} d=${row.featureDim ?? "?"}`;
  }
  return row.model.replaceAll("_", " ");
}

function rowsForSelection(data: DashboardData, selected: QmlEdgeRow): MetricRow[] {
  return data.metrics
    .filter((row) => row.trainSize === selected.trainSize && row.splitId === selected.splitId)
    .filter((row) => row.modelFamily === "classical" || row.featureDim === selected.featureDim)
    .sort((a, b) => b.rocAuc - a.rocAuc);
}

export function ModelArena({ data, selected }: ModelArenaProps): ReactElement {
  const rows = rowsForSelection(data, selected);
  const top = rows[0];
  const chartRows = rows.map((row) => ({
    name: modelLabel(row),
    rocAuc: row.rocAuc,
  }));

  return (
    <div className="dashboard-grid">
      <section className="panel primary-panel" aria-labelledby="arena-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Fair comparison</p>
            <h2 id="arena-title">Model Arena</h2>
          </div>
          <p>
            The selected walk-forward split keeps the same cutoff, target, and evaluation metrics for
            every model.
          </p>
        </div>

        <div className="chart-frame" aria-label="ROC-AUC leaderboard chart">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartRows} margin={{ top: 12, right: 20, bottom: 70, left: 10 }}>
              <CartesianGrid stroke="#d9dfdc" vertical={false} />
              <XAxis dataKey="name" angle={-30} interval={0} textAnchor="end" height={78} tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => fmt(Number(value))} />
              <Bar dataKey="rocAuc" name="ROC-AUC" fill="#0b8f89" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">Execution</th>
                <th scope="col">ROC-AUC</th>
                <th scope="col">Balanced acc.</th>
                <th scope="col">F1</th>
                <th scope="col">Top decile</th>
                <th scope="col">Signal return</th>
                <th scope="col">Max drawdown</th>
                <th scope="col">Train sec.</th>
                <th scope="col">Infer sec.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.model}-${row.executionMode}-${row.featureDim ?? "classical"}`}>
                  <td>{row.model.replaceAll("_", " ")}</td>
                  <td>{row.executionMode.replace("_", " ")}</td>
                  <td>{fmt(row.rocAuc)}</td>
                  <td>{fmt(row.balancedAccuracy)}</td>
                  <td>{fmt(row.f1)}</td>
                  <td>{fmt(row.precisionTopDecile)}</td>
                  <td>{fmt(row.signalReturnMean, 4)}</td>
                  <td>{fmt(row.maxDrawdown, 3)}</td>
                  <td>{fmt(row.trainSeconds, 4)}</td>
                  <td>{fmt(row.inferSeconds, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="panel detail-panel" aria-label="Arena summary">
        <p className="eyebrow">Selected split</p>
        <h3>{selected.splitId}</h3>
        <div className="metric-grid">
          <MetricTile label="Cutoff" value={selected.cutoffDate} tone="charcoal" />
          <MetricTile label="Train rows" value={String(selected.trainSize)} tone="teal" />
          <MetricTile label="Feature dim" value={String(selected.featureDim)} tone="amber" />
          <MetricTile label="Rows shown" value={String(rows.length)} tone="green" />
        </div>
        {top ? (
          <dl className="fact-list">
            <div>
              <dt>Top row</dt>
              <dd>{modelLabel(top)}</dd>
            </div>
            <div>
              <dt>ROC-AUC</dt>
              <dd>{fmt(top.rocAuc)}</dd>
            </div>
            <div>
              <dt>Market regime</dt>
              <dd>{selected.marketRegime.replace("_", " ")}</dd>
            </div>
            <div>
              <dt>Quantum features</dt>
              <dd>{selected.selectedFeatures || "Not recorded"}</dd>
            </div>
          </dl>
        ) : null}
        <p className="plain-note">
          This panel is intentionally strict: the quantum rows share the same selected split as the
          classical rows, so the comparison stays date-respecting.
        </p>
      </aside>
    </div>
  );
}
