import type { ReactElement } from "react";
import type { DashboardData, HeatmapCell, QmlEdgeRow } from "../types";
import { FigureGallery } from "./FigureGallery";
import { MetricTile } from "./MetricTile";

interface BoundaryMapProps {
  data: DashboardData;
  selected: QmlEdgeRow;
  onSelect: (edge: QmlEdgeRow) => void;
}

function fmt(value: number, digits = 3): string {
  return value.toFixed(digits);
}

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function cellColor(edge: number): string {
  if (edge >= 0.04) return "#1f8f48";
  if (edge >= 0.015) return "#68bd86";
  if (edge > 0) return "#cdeee5";
  if (edge <= -0.06) return "#c02776";
  if (edge <= -0.025) return "#e58ab6";
  if (edge < 0) return "#f5d5e4";
  return "#fff3cf";
}

function readableText(edge: number): string {
  return edge >= 0.04 || edge <= -0.06 ? "#ffffff" : "#202322";
}

function findCell(cells: HeatmapCell[], trainSize: number, featureDim: number): HeatmapCell | undefined {
  return cells.find((cell) => cell.trainSize === trainSize && cell.featureDim === featureDim);
}

export function BoundaryMap({ data, selected, onSelect }: BoundaryMapProps): ReactElement {
  return (
    <div className="dashboard-grid">
      <section className="panel primary-panel" aria-labelledby="boundary-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Classical ML vs QML</p>
            <h2 id="boundary-title">QML Edge Boundary Map</h2>
          </div>
          <p>
            Each cell averages QSVM statevector ROC-AUC minus the strongest classical ROC-AUC on the
            same walk-forward split.
          </p>
        </div>

        <div className="heatmap-wrap">
          <table className="heatmap" aria-label="QML ROC-AUC edge by training size and feature dimension">
            <thead>
              <tr>
                <th scope="col">Train size</th>
                {data.featureDims.map((featureDim) => (
                  <th scope="col" key={featureDim}>
                    d={featureDim}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.trainSizes.map((trainSize) => (
                <tr key={trainSize}>
                  <th scope="row">{trainSize}</th>
                  {data.featureDims.map((featureDim) => {
                    const cell = findCell(data.heatmapCells, trainSize, featureDim);
                    const isSelected =
                      selected.trainSize === trainSize && selected.featureDim === featureDim;
                    return (
                      <td key={`${trainSize}-${featureDim}`}>
                        {cell ? (
                          <button
                            className={isSelected ? "heatmap-cell selected" : "heatmap-cell"}
                            style={{
                              backgroundColor: cellColor(cell.meanEdge),
                              color: readableText(cell.meanEdge),
                            }}
                            type="button"
                            onClick={() => onSelect(cell.representative)}
                            aria-pressed={isSelected}
                            aria-label={`Training size ${trainSize}, feature dimension ${featureDim}, mean QML edge ${fmt(cell.meanEdge)}`}
                          >
                            <strong>{fmt(cell.meanEdge)}</strong>
                            <span>best {fmt(cell.bestEdge)}</span>
                          </button>
                        ) : (
                          <span className="empty-cell">No data</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <FigureGallery
          figures={[
            {
              src: `${import.meta.env.BASE_URL}figures/qml_edge_heatmap.png`,
              alt: "Generated QML edge heatmap",
              caption: "Generated benchmark heatmap",
            },
            {
              src: `${import.meta.env.BASE_URL}figures/score_cost_frontier.png`,
              alt: "Generated quantum score versus circuit cost frontier",
              caption: "Score versus circuit cost frontier",
            },
          ]}
        />
      </section>

      <aside className="panel detail-panel" aria-label="Selected boundary result">
        <p className="eyebrow">Selected cell</p>
        <h3>
          {selected.splitId} · d={selected.featureDim}
        </h3>
        <div className="metric-grid">
          <MetricTile label="QML edge" value={fmt(selected.qmlEdge)} tone={selected.qmlEdge >= 0 ? "green" : "magenta"} />
          <MetricTile label="QSVM ROC-AUC" value={fmt(selected.quantumRow.rocAuc)} tone="teal" />
          <MetricTile label="Best classical" value={fmt(selected.bestClassicalRow.rocAuc)} tone="amber" />
          <MetricTile label="Top decile" value={percent(selected.quantumRow.precisionTopDecile)} tone="charcoal" />
        </div>
        <dl className="fact-list">
          <div>
            <dt>Cutoff</dt>
            <dd>{selected.cutoffDate}</dd>
          </div>
          <div>
            <dt>Market regime</dt>
            <dd>{selected.marketRegime.replace("_", " ")}</dd>
          </div>
          <div>
            <dt>Best classical model</dt>
            <dd>{selected.bestClassicalRow.model.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>Selected quantum features</dt>
            <dd>{selected.selectedFeatures || "Not recorded"}</dd>
          </div>
        </dl>
        <p className="plain-note">
          This is a benchmark slice, not a market forecast. The useful result is the boundary where the
          quantum feature map is competitive enough to justify its circuit cost.
        </p>
      </aside>
    </div>
  );
}
