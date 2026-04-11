import type { ReactElement } from "react";

interface MetricTileProps {
  label: string;
  value: string;
  tone?: "teal" | "magenta" | "amber" | "green" | "charcoal";
}

export function MetricTile({ label, value, tone = "charcoal" }: MetricTileProps): ReactElement {
  return (
    <div className={`metric-tile metric-tile-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
