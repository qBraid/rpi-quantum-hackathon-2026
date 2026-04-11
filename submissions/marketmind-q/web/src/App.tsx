import { useEffect, useMemo, useState, type ReactElement } from "react";
import { BoundaryMap } from "./components/BoundaryMap";
import { JudgeTour } from "./components/JudgeTour";
import { MetricTile } from "./components/MetricTile";
import { ModelArena } from "./components/ModelArena";
import { QBraidLab } from "./components/QBraidLab";
import { StoryBridge } from "./components/StoryBridge";
import { loadDashboardData } from "./data";
import type { DashboardData, QmlEdgeRow, TabId } from "./types";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "boundary", label: "Boundary Map" },
  { id: "arena", label: "Model Arena" },
  { id: "qbraid", label: "qBraid Lab" },
  { id: "tour", label: "Judge Tour" },
];

function fmt(value: number, digits = 3): string {
  return value.toFixed(digits);
}

function initialSelection(data: DashboardData): QmlEdgeRow {
  return data.qmlEdges.reduce((best, row) => (row.qmlEdge > best.qmlEdge ? row : best), data.qmlEdges[0]);
}

function App(): ReactElement {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("boundary");
  const [selected, setSelected] = useState<QmlEdgeRow | null>(null);

  useEffect(() => {
    let active = true;
    loadDashboardData()
      .then((loaded) => {
        if (!active) return;
        setData(loaded);
        setSelected(initialSelection(loaded));
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(caught instanceof Error ? caught.message : "Could not load dashboard data.");
      });
    return () => {
      active = false;
    };
  }, []);

  const summary = useMemo(() => {
    if (!data) return null;
    const bestQuantum = data.metrics
      .filter((row) => row.modelFamily === "quantum")
      .reduce((best, row) => (row.rocAuc > best.rocAuc ? row : best));
    const bestClassical = data.metrics
      .filter((row) => row.modelFamily === "classical")
      .reduce((best, row) => (row.rocAuc > best.rocAuc ? row : best));
    const qbraidSuccesses = data.qbraidMetrics.filter((row) => row.status === "success").length;
    return {
      bestQuantum,
      bestClassical,
      qbraidSuccesses,
      qbraidRows: data.qbraidMetrics.length,
    };
  }, [data]);

  if (error) {
    return (
      <main className="app-shell">
        <section className="panel missing-panel">
          <p className="eyebrow">Dashboard data</p>
          <h1>Run the benchmark first</h1>
          <p>{error}</p>
          <pre>
            python -m src.run_benchmark --config configs/sector_etf.yaml{"\n"}
            python -m src.qbraid_benchmark --config configs/qbraid.yaml{"\n"}
            cd web && npm run sync-data
          </pre>
        </section>
      </main>
    );
  }

  if (!data || !selected || !summary) {
    return (
      <main className="app-shell">
        <section className="panel missing-panel">
          <p className="eyebrow">Loading</p>
          <h1>Preparing benchmark dashboard</h1>
          <p>Reading the frozen MarketMind-Q artifacts.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="MarketMind-Q logo" />
          <div>
            <p className="eyebrow">RPI Quantum Hackathon</p>
            <h1>MarketMind-Q Observatory</h1>
            <p className="subtitle">
              Static benchmark dashboard for finance QML boundaries and qBraid compiler-aware kernel
              preservation.
            </p>
          </div>
        </div>
        <div className="topbar-meta" aria-label="Dataset summary">
          <span>11 sector ETFs</span>
          <span>2018-01-01 to 2026-03-31</span>
          <span>SPY-relative five-day target</span>
        </div>
      </header>

      <section className="summary-strip" aria-label="Benchmark summary">
        <MetricTile label="Metric rows" value={String(data.metrics.length)} tone="charcoal" />
        <MetricTile label="Best classical ROC-AUC" value={fmt(summary.bestClassical.rocAuc)} tone="amber" />
        <MetricTile label="Best quantum ROC-AUC" value={fmt(summary.bestQuantum.rocAuc)} tone="teal" />
        <MetricTile label="qBraid success" value={`${summary.qbraidSuccesses}/${summary.qbraidRows}`} tone="green" />
      </section>

      <StoryBridge data={data} selected={selected} onOpenQBraid={() => setActiveTab("qbraid")} />

      <nav className="tabbar" aria-label="Dashboard sections">
        {tabs.map((tab) => (
          <button
            className={activeTab === tab.id ? "tab active" : "tab"}
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            aria-pressed={activeTab === tab.id}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "boundary" ? <BoundaryMap data={data} selected={selected} onSelect={setSelected} /> : null}
      {activeTab === "arena" ? <ModelArena data={data} selected={selected} /> : null}
      {activeTab === "qbraid" ? <QBraidLab data={data} /> : null}
      {activeTab === "tour" ? <JudgeTour /> : null}

      <footer className="app-footer">
        Research and education benchmark only. This dashboard does not recommend trades or forecast future
        market performance.
      </footer>
    </main>
  );
}

export default App;
