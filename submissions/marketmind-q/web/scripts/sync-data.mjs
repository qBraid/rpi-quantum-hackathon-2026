import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(scriptDir, "..");
const projectRoot = path.resolve(webRoot, "..");

const dataDir = path.join(webRoot, "public", "data");
const figuresDir = path.join(webRoot, "public", "figures");

mkdirSync(dataDir, { recursive: true });
mkdirSync(figuresDir, { recursive: true });

const files = [
  ["results/metrics_summary.csv", "public/data/metrics_summary.csv"],
  ["results/kernel_resources.csv", "public/data/kernel_resources.csv"],
  ["results/qbraid_compile_metrics.csv", "public/data/qbraid_compile_metrics.csv"],
  ["results/qbraid_path_summary.csv", "public/data/qbraid_path_summary.csv"],
  ["results/figures/qml_edge_heatmap.png", "public/figures/qml_edge_heatmap.png"],
  ["results/figures/score_cost_frontier.png", "public/figures/score_cost_frontier.png"],
  ["results/figures/qbraid_quality_cost.png", "public/figures/qbraid_quality_cost.png"],
  ["results/figures/qbraid_strategy_resources.png", "public/figures/qbraid_strategy_resources.png"],
];

let copied = 0;
for (const [from, to] of files) {
  const source = path.join(projectRoot, from);
  const destination = path.join(webRoot, to);
  if (!existsSync(source)) {
    console.warn(`missing artifact: ${from}`);
    continue;
  }
  mkdirSync(path.dirname(destination), { recursive: true });
  copyFileSync(source, destination);
  copied += 1;
}

console.log(`synced ${copied}/${files.length} benchmark artifacts`);
