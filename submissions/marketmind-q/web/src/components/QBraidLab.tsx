import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardData, QBraidSummary } from "../types";
import { FigureGallery } from "./FigureGallery";
import { MetricTile } from "./MetricTile";

interface QBraidLabProps {
  data: DashboardData;
}

function fmt(value: number, digits = 4): string {
  if (Math.abs(value) > 0 && Math.abs(value) < 0.0001) {
    return value.toExponential(2);
  }
  return value.toFixed(digits);
}

function label(row: QBraidSummary): string {
  return `${row.strategy.replace("_", " ")} · ${row.executionEnvironment.replace("_", " ")}`;
}

export function QBraidLab({ data }: QBraidLabProps): ReactElement {
  const summary = data.qbraidSummary.sort((a, b) => a.meanAbsProbabilityError - b.meanAbsProbabilityError);
  const best = summary[0];
  const chartRows = summary.map((row) => ({
    name: label(row),
    strategy: row.strategy,
    meanAbsProbabilityError: row.meanAbsProbabilityError,
    meanHellingerDistance: row.meanHellingerDistance,
    meanDepth: row.meanDepth,
    meanTwoQubitGates: row.meanTwoQubitGates,
  }));

  return (
    <div className="dashboard-grid">
      <section className="panel primary-panel" aria-labelledby="qbraid-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Compiler-aware quantum workload</p>
            <h2 id="qbraid-title">qBraid Lab</h2>
          </div>
          <p>
            The QSVM kernel circuit is compiled through qBraid and judged by probability preservation
            against compiled circuit cost.
          </p>
        </div>

        <div className="chart-pair">
          <div className="chart-frame" aria-label="qBraid output probability error">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartRows} margin={{ top: 12, right: 12, bottom: 76, left: 12 }}>
                <CartesianGrid stroke="#d9dfdc" vertical={false} />
                <XAxis dataKey="name" angle={-30} interval={0} textAnchor="end" height={84} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => fmt(Number(value))} />
                <Bar dataKey="meanAbsProbabilityError" name="Mean probability error" fill="#c02776" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-frame" aria-label="qBraid cost versus error frontier">
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart margin={{ top: 12, right: 24, bottom: 22, left: 8 }}>
                <CartesianGrid stroke="#d9dfdc" />
                <XAxis type="number" dataKey="meanTwoQubitGates" name="Two-qubit gates" tick={{ fontSize: 12 }} />
                <YAxis type="number" dataKey="meanAbsProbabilityError" name="Mean error" tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value) => fmt(Number(value))} />
                <Legend />
                <Scatter name="qBraid paths" data={chartRows} fill="#0b8f89" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Strategy</th>
                <th scope="col">Environment</th>
                <th scope="col">Rows</th>
                <th scope="col">Success</th>
                <th scope="col">Mean abs. error</th>
                <th scope="col">Max abs. error</th>
                <th scope="col">Hellinger</th>
                <th scope="col">Depth</th>
                <th scope="col">2Q gates</th>
                <th scope="col">Shots</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((row) => (
                <tr key={row.key}>
                  <td>{row.strategy.replace("_", " ")}</td>
                  <td>{row.executionEnvironment.replace("_", " ")}</td>
                  <td>{row.rows}</td>
                  <td>{row.successes}</td>
                  <td>{fmt(row.meanAbsProbabilityError)}</td>
                  <td>{fmt(row.maxAbsProbabilityError)}</td>
                  <td>{fmt(row.meanHellingerDistance)}</td>
                  <td>{fmt(row.meanDepth, 1)}</td>
                  <td>{fmt(row.meanTwoQubitGates, 1)}</td>
                  <td>{row.shots ?? "exact"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <FigureGallery
          figures={[
            {
              src: `${import.meta.env.BASE_URL}figures/qbraid_quality_cost.png`,
              alt: "Generated qBraid output error versus compiled cost chart",
              caption: "qBraid output error versus compiled cost",
            },
            {
              src: `${import.meta.env.BASE_URL}figures/qbraid_strategy_resources.png`,
              alt: "Generated qBraid strategy resource comparison",
              caption: "qBraid strategy resource comparison",
            },
          ]}
        />
      </section>

      <aside className="panel detail-panel" aria-label="qBraid summary">
        <p className="eyebrow">Best preservation path</p>
        {best ? (
          <>
            <h3>{label(best)}</h3>
            <div className="metric-grid">
              <MetricTile label="Mean error" value={fmt(best.meanAbsProbabilityError)} tone="green" />
              <MetricTile label="Depth" value={fmt(best.meanDepth, 1)} tone="teal" />
              <MetricTile label="2Q gates" value={fmt(best.meanTwoQubitGates, 1)} tone="amber" />
              <MetricTile label="Success" value={`${best.successes}/${best.rows}`} tone="charcoal" />
            </div>
          </>
        ) : null}
        <div className="path-list">
          <h4>qBraid conversion paths</h4>
          {data.qbraidPaths.map((path) => (
            <div className="path-row" key={`${path.source}-${path.target}`}>
              <strong>
                {path.source} to {path.target}
              </strong>
              <span>{path.shortestPath}</span>
              <small>
                {path.pathCount} path{path.pathCount === 1 ? "" : "s"} · qBraid {path.qbraidVersion}
              </small>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
