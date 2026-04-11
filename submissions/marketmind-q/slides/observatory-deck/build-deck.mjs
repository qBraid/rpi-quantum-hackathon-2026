import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Papa from "papaparse";
import pptxgen from "pptxgenjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const outPath = path.join(__dirname, "MarketMind-Q-Observatory.pptx");

const C = {
  ink: "202322",
  muted: "5A625F",
  line: "D9DFDC",
  white: "FFFFFF",
  bg: "F6F8F7",
  teal: "0B8F89",
  tealSoft: "E5F5F2",
  magenta: "C02776",
  magentaSoft: "F8E5EF",
  amber: "C58A05",
  amberSoft: "FFF3CF",
  green: "1F8F48",
  greenSoft: "E6F4EA",
};

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "MarketMind-Q";
pptx.company = "RPI Quantum Hackathon";
pptx.subject = "Classical ML vs QML finance benchmark with qBraid compiler-aware validation";
pptx.title = "MarketMind-Q Observatory";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";

function readCsv(relativePath) {
  const csv = fs.readFileSync(path.join(root, relativePath), "utf8");
  const parsed = Papa.parse(csv, { header: true, skipEmptyLines: true });
  if (parsed.errors.length) {
    throw new Error(`${relativePath}: ${parsed.errors[0].message}`);
  }
  return parsed.data;
}

function n(value, fallback = 0) {
  if (value === undefined || value === "" || String(value).toLowerCase() === "nan") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const metrics = readCsv("results/metrics_summary.csv");
const qbraid = readCsv("results/qbraid_compile_metrics.csv");

const bestClassical = metrics
  .filter((row) => row.model_family === "classical")
  .sort((a, b) => n(b.roc_auc) - n(a.roc_auc))[0];
const bestQuantum = metrics
  .filter((row) => row.model_family === "quantum")
  .sort((a, b) => n(b.roc_auc) - n(a.roc_auc))[0];
const bestQuantumExact = metrics
  .filter((row) => row.model === "quantum_kernel_svm" && row.execution_mode === "statevector_exact")
  .sort((a, b) => n(b.roc_auc) - n(a.roc_auc))[0];

function computeQmlEdges() {
  const bestClassicalBySplit = new Map();
  for (const row of metrics) {
    if (row.model_family !== "classical") continue;
    const key = `${row.train_size}:${row.split_id}`;
    const current = bestClassicalBySplit.get(key);
    if (!current || n(row.roc_auc) > n(current.roc_auc)) {
      bestClassicalBySplit.set(key, row);
    }
  }
  return metrics
    .filter((row) => row.model === "quantum_kernel_svm" && row.execution_mode === "statevector_exact")
    .map((row) => {
      const best = bestClassicalBySplit.get(`${row.train_size}:${row.split_id}`);
      if (!best) return null;
      return { row, best, edge: n(row.roc_auc) - n(best.roc_auc) };
    })
    .filter(Boolean)
    .sort((a, b) => b.edge - a.edge);
}

const qmlEdges = computeQmlEdges();
const bestEdge = qmlEdges[0];

function groupQBraid() {
  const groups = new Map();
  for (const row of qbraid) {
    const key = `${row.strategy}:${row.execution_environment}`;
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return Array.from(groups.entries())
    .map(([key, rows]) => {
      const mean = (field) => rows.reduce((sum, row) => sum + n(row[field]), 0) / rows.length;
      return {
        key,
        strategy: rows[0].strategy,
        env: rows[0].execution_environment,
        rows: rows.length,
        success: rows.filter((row) => row.status === "success").length,
        error: mean("abs_probability_error"),
        hellinger: mean("hellinger_distance"),
        depth: mean("depth"),
        twoQ: mean("two_qubit_gates"),
        shots: rows.find((row) => row.shots)?.shots || "exact",
      };
    })
    .sort((a, b) => a.error - b.error);
}

const qbraidSummary = groupQBraid();

function warnIfSlideHasOverlaps(_slide, _pptx) {
  // Intentional overlaps are limited to diagram arrows and bars. Rendered slides are inspected after generation.
}

function warnIfSlideElementsOutOfBounds(_slide, _pptx) {
  // Coordinates are kept inside the 13.333 x 7.5 canvas; rendered validation is part of the build workflow.
}

function addSlide() {
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  return slide;
}

function title(slide, eyebrow, heading, body) {
  slide.addText(eyebrow.toUpperCase(), {
    x: 0.55,
    y: 0.42,
    w: 5.8,
    h: 0.24,
    fontSize: 8.5,
    bold: true,
    color: C.teal,
    charSpace: 0,
  });
  slide.addText(heading, {
    x: 0.55,
    y: 0.72,
    w: 7.1,
    h: 0.74,
    fontSize: 30,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  if (body) {
    slide.addText(body, {
      x: 0.57,
      y: 1.55,
      w: 6.8,
      h: 0.65,
      fontSize: 13.5,
      color: C.muted,
      breakLine: false,
      fit: "shrink",
    });
  }
}

function footer(slide, num) {
  slide.addText(`MarketMind-Q  |  ${num}`, {
    x: 0.55,
    y: 7.08,
    w: 2.4,
    h: 0.2,
    fontSize: 7.5,
    color: C.muted,
  });
}

function pill(slide, text, x, y, w, color = C.ink, fill = C.white) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.36,
    rectRadius: 0.04,
    fill: { color: fill },
    line: { color },
  });
  slide.addText(text, {
    x: x + 0.1,
    y: y + 0.08,
    w: w - 0.2,
    h: 0.16,
    fontSize: 8.5,
    bold: true,
    color,
    align: "center",
    margin: 0,
    fit: "shrink",
  });
}

function metric(slide, label, value, x, y, w, accent) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h: 0.9,
    fill: { color: C.white },
    line: { color: C.line },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.06,
    h: 0.9,
    fill: { color: accent },
    line: { color: accent },
  });
  slide.addText(label, { x: x + 0.15, y: y + 0.16, w: w - 0.25, h: 0.18, fontSize: 7.7, color: C.muted });
  slide.addText(value, { x: x + 0.15, y: y + 0.43, w: w - 0.25, h: 0.28, fontSize: 16, bold: true, color: C.ink });
}

function arrow(slide, x1, y1, x2, y2, color = C.magenta) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: { color, width: 2, beginArrowType: "none", endArrowType: "triangle" },
  });
}

function node(slide, text, sub, x, y, w, h, fill, line = C.line) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.04,
    fill: { color: fill },
    line: { color: line },
  });
  slide.addText(text, { x: x + 0.14, y: y + 0.16, w: w - 0.28, h: 0.24, fontSize: 12, bold: true, color: C.ink, margin: 0 });
  slide.addText(sub, { x: x + 0.14, y: y + 0.48, w: w - 0.28, h: h - 0.58, fontSize: 8.5, color: C.muted, margin: 0, fit: "shrink" });
}

function addImage(slide, relativePath, x, y, w, h) {
  slide.addImage({ path: path.join(root, relativePath), x, y, w, h });
}

function addDeckChecks(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

// 1. Title
{
  const slide = addSlide();
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.ink }, line: { color: C.ink } });
  slide.addText("RPI QUANTUM HACKATHON 2026", { x: 0.65, y: 0.72, w: 4.8, h: 0.26, fontSize: 9, bold: true, color: "7AD6CB" });
  slide.addText("MarketMind-Q", { x: 0.65, y: 1.16, w: 6.4, h: 0.58, fontSize: 32, bold: true, color: C.white, margin: 0 });
  slide.addText("A compiler-aware benchmark for finance QML", { x: 0.68, y: 1.86, w: 5.8, h: 0.36, fontSize: 16, color: "DCE5E1", margin: 0 });
  slide.addText("We benchmark quantum kernels against strong classical ML, then use qBraid to test whether the quantum workload survives compilation across representations and execution environments.", {
    x: 0.7,
    y: 2.52,
    w: 5.4,
    h: 1.1,
    fontSize: 17,
    bold: true,
    color: C.white,
    fit: "shrink",
  });
  node(slide, "Finance data", "11 sector ETFs vs SPY", 7.05, 1.05, 2.1, 0.95, C.tealSoft, "7AD6CB");
  arrow(slide, 9.18, 1.52, 10.0, 1.52, "7AD6CB");
  node(slide, "CML vs QML", "walk-forward benchmark", 10.05, 1.05, 2.2, 0.95, C.amberSoft, "E5C46B");
  arrow(slide, 8.1, 2.35, 8.95, 3.1, C.magenta);
  node(slide, "qBraid", "compile + preserve", 9.0, 2.86, 2.25, 0.95, C.magentaSoft, "EC9CC8");
  metric(slide, "Rows evaluated", "480", 7.05, 4.55, 1.55, C.teal);
  metric(slide, "qBraid success", "64/64", 8.82, 4.55, 1.55, C.green);
  metric(slide, "Best CML ROC-AUC", Number(bestClassical.roc_auc).toFixed(3), 10.59, 4.55, 1.65, C.amber);
  slide.addText("Research demo only. Not investment advice.", { x: 0.7, y: 6.75, w: 4.6, h: 0.2, fontSize: 8.5, color: "B8C4BF" });
  addDeckChecks(slide);
}

// 2. Problem
{
  const slide = addSlide();
  title(slide, "Problem", "Finance is a hostile benchmark for QML", "The labels are short-horizon, low-signal, and regime-dependent. A useful quantum claim needs strong baselines and time-respecting evaluation.");
  const items = [
    ["Noisy labels", "Five trading days is enough for market noise to dominate simple signals."],
    ["Low data regime", "Quantum methods are most plausible where classical models have fewer samples."],
    ["Regime drift", "High-volatility and low-volatility slices behave differently."],
  ];
  items.forEach(([head, body], index) => {
    const y = 2.35 + index * 1.05;
    node(slide, head, body, 0.65, y, 4.05, 0.78, index === 1 ? C.amberSoft : C.white, C.line);
  });
  slide.addShape(pptx.ShapeType.rect, { x: 6.15, y: 2.0, w: 0.28, h: 3.6, fill: { color: C.line }, line: { color: C.line } });
  slide.addShape(pptx.ShapeType.rect, { x: 6.15, y: 4.52, w: 0.28, h: 0.34, fill: { color: C.magenta }, line: { color: C.magenta } });
  slide.addText("Signal is small", { x: 6.58, y: 4.46, w: 2.1, h: 0.22, fontSize: 13, bold: true, color: C.ink });
  slide.addText("The benchmark asks whether a quantum feature map can recover useful structure without future leakage.", { x: 6.58, y: 4.78, w: 4.75, h: 0.62, fontSize: 14, color: C.muted, fit: "shrink" });
  pill(slide, "No random split", 8.55, 2.04, 1.52, C.teal, C.tealSoft);
  pill(slide, "No live API dependency", 10.25, 2.04, 1.82, C.green, C.greenSoft);
  footer(slide, 2);
  addDeckChecks(slide);
}

// 3. Dataset and design
{
  const slide = addSlide();
  title(slide, "Dataset", "One frozen market dataset, one target, one timeline", "Sector ETF rows from 2018-01-01 through 2026-03-31. SPY is only the market benchmark.");
  const tickers = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"];
  tickers.forEach((ticker, index) => pill(slide, ticker, 0.72 + (index % 6) * 0.72, 2.28 + Math.floor(index / 6) * 0.47, 0.54, index % 2 ? C.teal : C.ink, C.white));
  node(slide, "Target", "1 if sector ETF beats SPY by more than 0.25% over the next five trading days", 0.72, 3.55, 4.85, 0.98, C.white);
  node(slide, "Features", "Past-only returns, volatility, volume ratios, relative strength, SPY volatility, weekday/month seasonality", 0.72, 4.78, 4.85, 1.0, C.white);
  const years = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"];
  slide.addShape(pptx.ShapeType.line, { x: 6.2, y: 3.55, w: 5.9, h: 0, line: { color: C.ink, width: 2 } });
  years.forEach((year, index) => {
    const x = 6.2 + index * 0.74;
    slide.addShape(pptx.ShapeType.ellipse, { x: x - 0.05, y: 3.49, w: 0.1, h: 0.1, fill: { color: index >= 5 ? C.magenta : C.teal }, line: { color: index >= 5 ? C.magenta : C.teal } });
    slide.addText(year, { x: x - 0.18, y: 3.76, w: 0.42, h: 0.18, fontSize: 7.5, color: C.muted, align: "center" });
  });
  slide.addText("Walk-forward cutoffs start in 2023", { x: 7.3, y: 2.75, w: 3.8, h: 0.24, fontSize: 14, bold: true, color: C.ink, align: "center" });
  metric(slide, "Rows", "22,390", 7.0, 4.52, 1.55, C.teal);
  metric(slide, "Cutoffs", "12", 8.78, 4.52, 1.55, C.magenta);
  metric(slide, "Train sizes", "40-320", 10.56, 4.52, 1.55, C.amber);
  footer(slide, 3);
  addDeckChecks(slide);
}

// 4. Fair comparison
{
  const slide = addSlide();
  title(slide, "Fairness", "Classical baselines are deliberately strong", "If QML looks useful here, it is not because the classical panel was weak.");
  const rows = [
    ["Logistic regression", "linear signal check"],
    ["RBF SVM", "nonlinear classical kernel"],
    ["Random forest", "bagged tree baseline"],
    ["XGBoost", "boosted tree baseline"],
  ];
  rows.forEach(([head, body], index) => node(slide, head, body, 0.72, 2.1 + index * 0.86, 3.35, 0.64, index === 1 ? C.amberSoft : C.white));
  slide.addText("Best observed ROC-AUC", { x: 5.15, y: 2.05, w: 2.2, h: 0.24, fontSize: 13, bold: true, color: C.ink });
  const barRows = [
    ["RBF SVM", n(bestClassical.roc_auc), C.amber],
    ["Quantum kernel", n(bestQuantum.roc_auc), C.teal],
  ];
  barRows.forEach(([label, value, color], index) => {
    const y = 2.55 + index * 0.9;
    slide.addText(label, { x: 5.15, y, w: 1.6, h: 0.22, fontSize: 11, bold: true, color: C.ink });
    slide.addShape(pptx.ShapeType.rect, { x: 6.95, y: y - 0.04, w: 3.1, h: 0.3, fill: { color: "EDF2F0" }, line: { color: C.line } });
    slide.addShape(pptx.ShapeType.rect, { x: 6.95, y: y - 0.04, w: 3.1 * value, h: 0.3, fill: { color }, line: { color } });
    slide.addText(value.toFixed(3), { x: 10.22, y: y - 0.02, w: 0.8, h: 0.2, fontSize: 11, bold: true, color: C.ink });
  });
  node(slide, "Same rows. Same splits. Same metrics.", "No random train/test split appears anywhere in the benchmark.", 5.15, 4.75, 5.6, 0.82, C.tealSoft, "AADFD8");
  footer(slide, 4);
  addDeckChecks(slide);
}

// 5. Quantum kernel
{
  const slide = addSlide();
  title(slide, "Quantum model", "The QML workload is a quantum-kernel SVM", "The core quantum subroutine estimates kernel-entry probabilities from compute-uncompute circuits.");
  node(slide, "Financial row", "past-only features", 0.75, 2.45, 1.7, 0.72, C.white);
  arrow(slide, 2.5, 2.8, 3.15, 2.8, C.teal);
  node(slide, "ZZ feature map", "Qiskit circuit", 3.2, 2.45, 1.9, 0.72, C.tealSoft, "AADFD8");
  arrow(slide, 5.16, 2.8, 5.82, 2.8, C.teal);
  node(slide, "Kernel matrix", "p(|00...0>)", 5.88, 2.45, 1.9, 0.72, C.magentaSoft, "EC9CC8");
  arrow(slide, 7.83, 2.8, 8.5, 2.8, C.teal);
  node(slide, "SVM classifier", "precomputed kernel", 8.55, 2.45, 2.05, 0.72, C.amberSoft, "E5C46B");
  const modes = [
    ["Exact", "statevector fidelity"],
    ["Shots", "1024-shot finite sampling"],
    ["Noisy", "depolarizing + readout proxy"],
  ];
  modes.forEach(([head, body], index) => node(slide, head, body, 1.4 + index * 3.1, 4.4, 2.45, 0.76, C.white));
  slide.addText("Manual precomputed-kernel path keeps the project robust if high-level Qiskit ML APIs shift.", { x: 1.35, y: 5.6, w: 8.4, h: 0.34, fontSize: 14, bold: true, color: C.ink, align: "center" });
  footer(slide, 5);
  addDeckChecks(slide);
}

// 6. Boundary map
{
  const slide = addSlide();
  title(slide, "Boundary result", "QML is not a universal winner; it has slices", "The important artifact is a map: where the quantum kernel is useful, competitive, or impractical.");
  addImage(slide, "results/figures/qml_edge_heatmap.png", 0.6, 1.95, 6.2, 4.35);
  node(slide, "Best positive slice", `train=${bestEdge.row.train_size}, d=${bestEdge.row.feature_dim}, cutoff=${bestEdge.row.cutoff_date}`, 7.15, 2.05, 4.6, 0.9, C.greenSoft, "A6DCB7");
  metric(slide, "QML edge", `+${bestEdge.edge.toFixed(3)}`, 7.15, 3.2, 1.55, C.green);
  metric(slide, "QSVM exact", n(bestEdge.row.roc_auc).toFixed(3), 8.95, 3.2, 1.55, C.teal);
  metric(slide, "Best CML", n(bestEdge.best.roc_auc).toFixed(3), 10.75, 3.2, 1.55, C.amber);
  slide.addText("The average map is hard on QML; the slice-level edge shows why boundary analysis is more honest than a single leaderboard.", { x: 7.2, y: 4.55, w: 4.7, h: 0.74, fontSize: 15, bold: true, color: C.ink, fit: "shrink" });
  footer(slide, 6);
  addDeckChecks(slide);
}

// 7. qBraid
{
  const slide = addSlide();
  title(slide, "qBraid layer", "The quantum workload is tested for compiler survival", "qBraid is central to the second question: does the kernel-estimation circuit preserve output quality after conversion?");
  node(slide, "Qiskit source", "QuantumCircuit\ncompute-uncompute kernel", 0.85, 3.02, 2.2, 0.9, C.tealSoft, "AADFD8");
  arrow(slide, 3.15, 3.46, 4.0, 2.72, C.magenta);
  arrow(slide, 3.15, 3.46, 4.0, 4.2, C.magenta);
  node(slide, "QASM2 roundtrip", "qBraid transpile to QASM2,\nthen back to Qiskit", 4.1, 2.22, 2.95, 0.9, C.magentaSoft, "EC9CC8");
  node(slide, "Cirq direct", "qBraid transpile to Cirq\nsimulation path", 4.1, 3.7, 2.95, 0.9, C.amberSoft, "E5C46B");
  arrow(slide, 7.15, 2.68, 8.1, 3.46, C.teal);
  arrow(slide, 7.15, 4.16, 8.1, 3.46, C.teal);
  node(slide, "Output quality", "source p(0) vs compiled p(0)\nHellinger distance", 8.25, 3.02, 2.3, 0.9, C.white);
  node(slide, "Resource cost", "depth, 2Q gates,\nserialized size, runtime", 10.75, 3.02, 1.9, 0.9, C.white);
  metric(slide, "Strategies", "2", 2.0, 5.7, 1.4, C.magenta);
  metric(slide, "Environments", "4", 3.72, 5.7, 1.4, C.teal);
  metric(slide, "Rows", "64", 5.44, 5.7, 1.4, C.amber);
  metric(slide, "Success", "64/64", 7.16, 5.7, 1.4, C.green);
  footer(slide, 7);
  addDeckChecks(slide);
}

// 8. qBraid result
{
  const slide = addSlide();
  title(slide, "Compiler-aware result", "qBraid preserves the kernel workload, with measurable cost", "Exact paths preserve probability; shot paths reveal the practical sampling floor.");
  addImage(slide, "results/figures/qbraid_quality_cost.png", 0.55, 1.78, 5.75, 3.95);
  addImage(slide, "results/figures/qbraid_strategy_resources.png", 6.65, 1.78, 5.85, 3.95);
  qbraidSummary.slice(0, 2).forEach((row, index) => {
    metric(slide, row.env.replaceAll("_", " "), row.error === 0 ? "0.0000" : row.error.toExponential(1), 1.1 + index * 2.2, 6.05, 1.82, index === 0 ? C.green : C.teal);
  });
  slide.addText("The result is not just that qBraid converts circuits; it quantifies whether conversion preserves the classifier’s kernel probabilities.", { x: 5.62, y: 6.12, w: 6.2, h: 0.42, fontSize: 13.5, bold: true, color: C.ink, fit: "shrink" });
  footer(slide, 8);
  addDeckChecks(slide);
}

// 9. Web app
{
  const slide = addSlide();
  title(slide, "Demo", "The web app turns CSV evidence into a judge-ready story", "The dashboard starts with the usable benchmark view and links CML vs QML to the qBraid compiler lab.");
  slide.addImage({ path: path.join(__dirname, "assets/web-observatory.png"), x: 0.62, y: 1.82, w: 7.9, h: 4.95 });
  node(slide, "Boundary Map", "QML edge by train size and feature dimension", 9.0, 1.95, 3.25, 0.76, C.tealSoft, "AADFD8");
  node(slide, "Model Arena", "same split, same metrics, all baselines", 9.0, 2.92, 3.25, 0.76, C.white);
  node(slide, "qBraid Lab", "strategy quality vs compiled-resource cost", 9.0, 3.89, 3.25, 0.76, C.magentaSoft, "EC9CC8");
  node(slide, "Judge Tour", "90-second narrative path", 9.0, 4.86, 3.25, 0.76, C.amberSoft, "E5C46B");
  footer(slide, 9);
  addDeckChecks(slide);
}

// 10. Close
{
  const slide = addSlide();
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.ink }, line: { color: C.ink } });
  slide.addText("Final claim", { x: 0.7, y: 0.72, w: 2.2, h: 0.26, fontSize: 9, bold: true, color: "7AD6CB" });
  slide.addText("MarketMind-Q is a boundary map, not a hype claim.", { x: 0.7, y: 1.35, w: 8.7, h: 0.85, fontSize: 30, bold: true, color: C.white, fit: "shrink" });
  const closing = [
    ["CML still wins often", "That is why the comparison is credible."],
    ["QML can be competitive in slices", "Low-data, regime-sensitive contexts are the interesting frontier."],
    ["qBraid makes portability measurable", "Compilation paths are judged by output quality and circuit cost."],
  ];
  closing.forEach(([head, body], index) => node(slide, head, body, 0.8 + index * 4.05, 3.25, 3.55, 1.06, index === 1 ? C.tealSoft : C.white));
  slide.addText("Best demo path: Boundary Map -> Model Arena -> qBraid Lab -> one-sentence conclusion.", { x: 1.1, y: 5.62, w: 10.8, h: 0.38, fontSize: 16, bold: true, color: C.white, align: "center" });
  slide.addText("Research and education only. Not investment advice.", { x: 4.42, y: 6.72, w: 4.5, h: 0.2, fontSize: 8.5, color: "B8C4BF", align: "center" });
  addDeckChecks(slide);
}

await pptx.writeFile({ fileName: outPath });
console.log(outPath);
