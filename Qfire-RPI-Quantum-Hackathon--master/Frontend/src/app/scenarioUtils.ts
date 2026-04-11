import type { CellState } from "./types";

export const CELL_OPTIONS: CellState[] = [
  "empty",
  "road_or_firebreak",
  "dry_brush",
  "grass",
  "shrub",
  "tree",
  "water",
  "protected",
  "intervention",
  "ignition",
  "burned",
];

export function blankGrid(fill: CellState = "tree"): CellState[][] {
  return Array.from({ length: 10 }, () => Array.from({ length: 10 }, () => fill));
}

export function stateTone(state: CellState) {
  switch (state) {
    case "ignition":
      return "warn";
    case "protected":
    case "intervention":
      return "accent";
    case "road_or_firebreak":
      return "neutral";
    case "water":
      return "good";
    case "burned":
      return "warn";
    default:
      return "neutral";
  }
}
