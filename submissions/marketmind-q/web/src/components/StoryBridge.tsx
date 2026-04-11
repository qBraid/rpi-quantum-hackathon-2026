import type { ReactElement } from "react";
import type { DashboardData, QBraidSummary, QmlEdgeRow } from "../types";

interface StoryBridgeProps {
  data: DashboardData;
  selected: QmlEdgeRow;
  onOpenQBraid: () => void;
}

function fmt(value: number, digits = 3): string {
  if (Math.abs(value) > 0 && Math.abs(value) < 0.0001) {
    return value.toExponential(1);
  }
  return value.toFixed(digits);
}

function modelName(value: string): string {
  return value.replaceAll("_", " ");
}

function bestExactPath(summary: QBraidSummary[]): QBraidSummary | undefined {
  const exactRows = summary.filter((row) => row.shots === null);
  return exactRows.reduce<QBraidSummary | undefined>((best, row) => {
    if (!best || row.meanAbsProbabilityError < best.meanAbsProbabilityError) {
      return row;
    }
    return best;
  }, undefined);
}

export function StoryBridge({ data, selected, onOpenQBraid }: StoryBridgeProps): ReactElement {
  const exactPath = bestExactPath(data.qbraidSummary);
  const cmlScore = selected.bestClassicalRow.rocAuc;
  const qmlScore = selected.quantumRow.rocAuc;
  const cmlWidth = `${Math.max(8, Math.min(100, cmlScore * 100))}%`;
  const qmlWidth = `${Math.max(8, Math.min(100, qmlScore * 100))}%`;
  const edgeSign = selected.qmlEdge >= 0 ? "+" : "";

  return (
    <section className="story-board" aria-label="MarketMind-Q story">
      <div className="story-copy">
        <p className="eyebrow">Demo path</p>
        <h2>From finance signal to quantum portability</h2>
        <p>
          Start with a date-respecting benchmark, compare the strongest classical model against the
          quantum kernel, then use qBraid to test whether the winning quantum workload survives
          compilation.
        </p>
      </div>

      <div className="duel-visual" aria-label="Classical versus quantum comparison">
        <div className="duel-row">
          <div className="duel-label">
            <strong>CML champion</strong>
            <span>{modelName(selected.bestClassicalRow.model)}</span>
          </div>
          <div className="duel-track">
            <span className="duel-bar cml-bar" style={{ width: cmlWidth }} />
            <b>{fmt(cmlScore)}</b>
          </div>
        </div>
        <div className="duel-row">
          <div className="duel-label">
            <strong>QML kernel</strong>
            <span>QSVM statevector d={selected.featureDim}</span>
          </div>
          <div className="duel-track">
            <span className="duel-bar qml-bar" style={{ width: qmlWidth }} />
            <b>{fmt(qmlScore)}</b>
          </div>
        </div>
        <div className={selected.qmlEdge >= 0 ? "edge-callout positive" : "edge-callout negative"}>
          <span>ROC-AUC edge</span>
          <strong>
            {edgeSign}
            {fmt(selected.qmlEdge)}
          </strong>
        </div>
      </div>

      <div className="compiler-visual" aria-label="qBraid compiler bridge">
        <div className="source-node">
          <span>Qiskit source</span>
          <strong>kernel circuit</strong>
        </div>
        <div className="bridge-lines" aria-hidden="true">
          <span />
          <span />
        </div>
        <div className="compiled-nodes">
          <div>
            <span>QASM2 roundtrip</span>
            <strong>exact path</strong>
          </div>
          <div>
            <span>Cirq direct</span>
            <strong>portable path</strong>
          </div>
        </div>
        <button className="story-link" type="button" onClick={onOpenQBraid}>
          qBraid Lab
        </button>
        {exactPath ? (
          <p>
            Best exact compiler path: {exactPath.strategy.replace("_", " ")} with mean error{" "}
            {fmt(exactPath.meanAbsProbabilityError, 4)}.
          </p>
        ) : null}
      </div>
    </section>
  );
}
