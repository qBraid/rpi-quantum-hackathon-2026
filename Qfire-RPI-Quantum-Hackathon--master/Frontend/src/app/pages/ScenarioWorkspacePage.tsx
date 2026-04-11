import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ChevronLeft, Play, Save, Trash2 } from "lucide-react";

import { api } from "../api";
import { EmptyState, LoadingState, Notice, PageHeader, ScenarioGrid, SectionPanel, StatusPill } from "../components/product";
import { blankGrid, CELL_OPTIONS } from "../scenarioUtils";
import type { CellState, ScenarioPayload } from "../types";

const templates: Array<{ key: string; label: string; payload: ScenarioPayload }> = [
  {
    key: "base",
    label: "Planning baseline",
    payload: {
      name: "Planning baseline",
      domain: "wildfire",
      status: "draft",
      description: "Balanced preseason planning scenario with mixed fuels, one ignition source, and standard treatment budget assumptions.",
      grid: blankGrid(),
      metadata_json: { region: "Unassigned", owner: "Wildfire West" },
      constraints_json: {
        intervention_budget_k: 10,
        crew_limit: 3,
        time_horizon_hours: 72,
        spread_sensitivity: 0.64,
        dryness: 0.62,
        wind_speed: 0.48,
        wind_direction: "north_east",
        spotting_likelihood: 0.08,
      },
      objectives_json: { primary: "reduce burn probability and break likely spread corridors" },
    },
  },
  {
    key: "wind",
    label: "Canyon wind corridor",
    payload: {
      name: "Canyon wind corridor",
      domain: "wildfire",
      status: "draft",
      description: "Steep corridor where aligned wind can push fire through dense brush and shrub patches toward a treated edge.",
      grid: blankGrid().map((row, rowIndex) =>
        row.map((_, colIndex) => {
          if (rowIndex === 1 && colIndex === 1) return "ignition";
          if (colIndex === 0 || colIndex === 9) return "road_or_firebreak";
          if (rowIndex >= 2 && rowIndex <= 6 && colIndex >= 2 && colIndex <= 7) return colIndex % 2 === 0 ? "dry_brush" : "shrub";
          if (colIndex === 8) return "protected";
          return rowIndex >= 7 ? "tree" : "grass";
        }),
      ),
      metadata_json: { region: "Foothill corridor", owner: "Wildfire West" },
      constraints_json: {
        intervention_budget_k: 10,
        crew_limit: 2,
        time_horizon_hours: 48,
        spread_sensitivity: 0.72,
        dryness: 0.78,
        wind_speed: 0.74,
        wind_direction: "east",
        spotting_likelihood: 0.12,
      },
      objectives_json: { primary: "protect the east perimeter while delaying the canyon ignition front" },
    },
  },
  {
    key: "interface",
    label: "Patchy WUI edge",
    payload: {
      name: "Patchy WUI edge",
      domain: "wildfire",
      status: "draft",
      description: "Patchy wildland-urban interface with mixed vegetation, water breaks, and partial hardening near exposed structures.",
      grid: blankGrid().map((row, rowIndex) =>
        row.map((_, colIndex) => {
          if (rowIndex === 2 && colIndex === 2) return "ignition";
          if (rowIndex >= 1 && rowIndex <= 6 && colIndex >= 1 && colIndex <= 5) return rowIndex % 2 === 0 ? "dry_brush" : "grass";
          if (colIndex >= 7) return "protected";
          if (rowIndex === 8 || rowIndex === 9) return "water";
          return colIndex % 3 === 0 ? "tree" : "shrub";
        }),
      ),
      metadata_json: { region: "Interface zone", owner: "Operations" },
      constraints_json: {
        intervention_budget_k: 10,
        crew_limit: 4,
        time_horizon_hours: 72,
        spread_sensitivity: 0.58,
        dryness: 0.55,
        wind_speed: 0.34,
        wind_direction: "south_east",
        spotting_likelihood: 0.07,
      },
      objectives_json: { primary: "reduce spread into the protected interface edge" },
    },
  },
];

function clonePayload(payload: ScenarioPayload): ScenarioPayload {
  return JSON.parse(JSON.stringify(payload)) as ScenarioPayload;
}

export function ScenarioWorkspacePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [payload, setPayload] = useState<ScenarioPayload>(clonePayload(templates[0].payload));
  const [loading, setLoading] = useState(Boolean(id));
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ tone: "success" | "error" | "info"; title: string; description: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<[number, number] | null>(null);
  const [brushState, setBrushState] = useState<CellState>("dry_brush");
  const [scenarioId, setScenarioId] = useState<string | null>(id ?? null);
  const [scenarioVersion, setScenarioVersion] = useState<number | null>(null);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        setLoading(true);
        const scenario = await api.getScenario(id);
        if (cancelled) return;
        setScenarioId(scenario.id);
        setScenarioVersion(scenario.version);
        setPayload({
          name: scenario.name,
          domain: scenario.domain,
          status: scenario.status,
          description: scenario.description,
          grid: scenario.grid,
          metadata_json: scenario.metadata_json,
          constraints_json: scenario.constraints_json,
          objectives_json: scenario.objectives_json,
        });
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load scenario");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const selectedState = useMemo(
    () => (selectedCell ? payload.grid[selectedCell[0]][selectedCell[1]] : null),
    [payload.grid, selectedCell],
  );

  function applyTemplate(templateKey: string) {
    const template = templates.find((item) => item.key === templateKey);
    if (!template) return;
    setPayload(clonePayload(template.payload));
    setSelectedCell(null);
    setStatusMessage({
      tone: "info",
      title: "Template applied",
      description: `${template.label} loaded into the workspace. Save to persist it as a scenario version.`,
    });
  }

  function updateGridCell(row: number, col: number) {
    setSelectedCell([row, col]);
    setPayload((current) => ({
      ...current,
      grid: current.grid.map((gridRow, rowIndex) =>
        gridRow.map((cell, colIndex) => (rowIndex === row && colIndex === col ? brushState : cell)),
      ),
    }));
  }

  async function saveScenario() {
    setSaving(true);
    setError(null);
    try {
      const saved = scenarioId ? await api.updateScenario(scenarioId, payload) : await api.createScenario(payload);
      setScenarioId(saved.id);
      setScenarioVersion(saved.version);
      setStatusMessage({
        tone: "success",
        title: "Scenario saved",
        description: `Version ${saved.version} is now persisted and available to risk, forecast, optimization, benchmarks, and reports.`,
      });
      if (!scenarioId) {
        navigate(`/app/scenarios/${saved.id}`, { replace: true });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save scenario";
      setError(message);
      setStatusMessage({ tone: "error", title: "Save failed", description: message });
    } finally {
      setSaving(false);
    }
  }

  async function archiveScenario() {
    if (!scenarioId) return;
    if (!window.confirm("Archive this scenario? It will remain available in history but marked inactive.")) {
      return;
    }
    const updated = await api.updateScenario(scenarioId, { archived: true, status: "archived" });
    setScenarioVersion(updated.version);
    setPayload((current) => ({ ...current, status: updated.status }));
    setStatusMessage({
      tone: "success",
      title: "Scenario archived",
      description: "The scenario remains versioned and retrievable, but it is now marked archived.",
    });
  }

  async function deleteScenario() {
    if (!scenarioId) return;
    if (!window.confirm("Delete this scenario permanently? Existing runs remain in the database but this scenario record will be removed.")) {
      return;
    }
    await api.deleteScenario(scenarioId);
    navigate("/app/scenarios");
  }

  if (loading) return <LoadingState label="Loading scenario workspace..." />;
  if (error && !scenarioId) {
    return <EmptyState title="Scenario unavailable" description={error} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/app/scenarios" className="inline-flex items-center gap-2 text-[13px] text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Back to scenarios
        </Link>
        <div className="flex items-center gap-2">
          {scenarioVersion ? <StatusPill label={`v${scenarioVersion}`} tone="accent" /> : null}
          <StatusPill label={payload.status} tone={payload.status === "archived" ? "warn" : "neutral"} />
        </div>
      </div>

      <PageHeader
        eyebrow="Step 1 - Scenario setup"
        title={payload.name}
        description="Edit fuels, barriers, and ignition points, define planning conditions, and save a clean hillside version before running risk, ensemble spread, and intervention planning."
        actions={
          <>
            {scenarioId ? (
              <button onClick={() => void archiveScenario()} className="border border-border bg-card px-6 py-2.5 text-[12px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                Archive
              </button>
            ) : null}
            {scenarioId ? (
              <button onClick={() => void deleteScenario()} className="border border-qp-red/40 bg-card px-5 py-2.5 text-[12px] font-bold uppercase tracking-wider text-qp-red hover:bg-qp-red hover:text-white transition-colors">
                <span className="inline-flex items-center gap-2">
                  <Trash2 className="h-4 w-4" /> Delete
                </span>
              </button>
            ) : null}
            <button
              onClick={() => void saveScenario()}
              disabled={saving}
              className="border border-border bg-card px-6 py-2.5 text-[12px] font-bold uppercase tracking-wider text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
            >
              <span className="inline-flex items-center gap-2">
                <Save className="h-4 w-4" /> {saving ? "Saving..." : "Save"}
              </span>
            </button>
            {scenarioId ? (
              <Link to={`/app/risk?scenario=${scenarioId}`} className="border border-transparent bg-primary px-6 py-2.5 text-[12px] font-bold uppercase tracking-wider text-primary-foreground hover:bg-qp-slate transition-colors">
                <span className="inline-flex items-center gap-2">
                  <Play className="h-4 w-4" /> Continue
                </span>
              </Link>
            ) : null}
          </>
        }
      />

      {statusMessage ? <Notice tone={statusMessage.tone} title={statusMessage.title} description={statusMessage.description} /> : null}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)_300px]">
        <SectionPanel title="Scenario inputs" subtitle="Templates, planning assumptions, and the core controls that define one preseason wildfire planning case">
          <div className="space-y-4 text-[13px]">
            <div>
              <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground text-qp-cyan">Template</label>
              <select onChange={(event) => applyTemplate(event.target.value)} defaultValue="" className="w-full border border-border bg-card px-4 py-2.5 text-[14px] outline-none focus:border-primary transition-colors">
                <option value="" disabled>
                  Load a template
                </option>
                {templates.map((template) => (
                  <option key={template.key} value={template.key}>
                    {template.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Name</label>
              <input
                value={payload.name}
                onChange={(event) => setPayload((current) => ({ ...current, name: event.target.value }))}
                className="w-full border border-border bg-card px-4 py-2.5 text-[14px] outline-none focus:border-primary transition-colors"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Description</label>
              <textarea
                value={payload.description}
                onChange={(event) => setPayload((current) => ({ ...current, description: event.target.value }))}
                className="min-h-[100px] w-full border border-border bg-card px-4 py-3 text-[14px] leading-relaxed outline-none focus:border-primary transition-colors"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Intervention budget (K)</label>
                <input
                  type="number"
                  min={1}
                  value={String(payload.constraints_json.intervention_budget_k ?? 10)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, intervention_budget_k: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Crew limit</label>
                <input
                  type="number"
                  min={1}
                  value={String(payload.constraints_json.crew_limit ?? 3)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, crew_limit: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Planning horizon (hrs)</label>
                <input
                  type="number"
                  min={1}
                  value={String(payload.constraints_json.time_horizon_hours ?? 72)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, time_horizon_hours: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Spread sensitivity</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={String(payload.constraints_json.spread_sensitivity ?? 0.64)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, spread_sensitivity: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Dryness</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={String(payload.constraints_json.dryness ?? 0.6)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, dryness: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Wind speed</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={String(payload.constraints_json.wind_speed ?? 0.4)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, wind_speed: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Spotting likelihood</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={String(payload.constraints_json.spotting_likelihood ?? 0.08)}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, spotting_likelihood: Number(event.target.value) },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] font-mono outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Wind direction</label>
                <select
                  value={String(payload.constraints_json.wind_direction ?? "east")}
                  onChange={(event) =>
                    setPayload((current) => ({
                      ...current,
                      constraints_json: { ...current.constraints_json, wind_direction: event.target.value },
                    }))
                  }
                  className="w-full border border-border bg-card px-4 py-2.5 text-[14px] outline-none focus:border-primary transition-colors"
                >
                  {[
                    "north",
                    "north_east",
                    "east",
                    "south_east",
                    "south",
                    "south_west",
                    "west",
                    "north_west",
                  ].map((option) => (
                    <option key={option} value={option}>
                      {option.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Primary objective</label>
              <input
                value={String(payload.objectives_json.primary ?? "")}
                onChange={(event) =>
                  setPayload((current) => ({
                    ...current,
                    objectives_json: { ...current.objectives_json, primary: event.target.value },
                  }))
                }
                className="w-full border border-border bg-card px-4 py-2.5 text-[14px] outline-none focus:border-primary transition-colors"
              />
            </div>
          </div>
        </SectionPanel>

        <SectionPanel title="10x10 hillside grid" subtitle="Choose a cell type, then paint fuels, barriers, treatments, and ignition directly onto the hillside. This grid becomes the source of truth for risk, forecast, and optimization.">
          <ScenarioGrid grid={payload.grid} selected={selectedCell} editable onSelect={updateGridCell} brushState={brushState} />
        </SectionPanel>

        <SectionPanel title="Cell legend and inspector" subtitle="Use the legend to mark fuel classes, hard breaks, treatment, and ignition sources">
          <div className="flex flex-col h-full space-y-5">
            <div className="flex flex-wrap gap-2">
              {CELL_OPTIONS.map((state) => (
                <button
                  key={state}
                  onClick={() => setBrushState(state)}
                  className={`border px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-all ${
                    brushState === state ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card text-muted-foreground hover:bg-secondary"
                  }`}
                >
                  {state.replace("_", " ")}
                </button>
              ))}
            </div>
            <div className="border border-border bg-card p-4 mt-2">
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                <span className="font-bold text-foreground">Dry brush</span> is the fastest-burning fuel, <span className="font-bold text-foreground">grass</span> and <span className="font-bold text-foreground">shrub</span> carry fire differently, <span className="font-bold text-foreground">tree</span> holds more fuel. <span className="font-bold text-foreground">Intervention</span> and <span className="font-bold text-foreground">protected</span> cells reduce ignition probability, and <span className="font-bold text-foreground">water</span> or <span className="font-bold text-foreground">roads</span> act as hard breaks.
              </p>
            </div>
            <div className="border border-border bg-card p-5 mt-4 border-l-2 border-l-qp-cyan">
              <p className="text-[12px] uppercase tracking-[0.15em] font-bold text-muted-foreground mb-3">Selected cell</p>
              {selectedCell ? (
                <>
                  <p className="text-[18px] font-bold text-foreground">
                    Row {selectedCell[0] + 1}, Col {selectedCell[1] + 1}
                  </p>
                  <p className="mt-1 text-[13px] text-muted-foreground font-medium">State: <span className="text-foreground">{selectedState?.replace("_", " ")}</span></p>
                </>
              ) : (
                <p className="text-[13px] text-muted-foreground">Select a cell to inspect it.</p>
              )}
            </div>
            {scenarioId ? (
              <div className="border border-border bg-card p-5 mt-4">
                <p className="text-[12px] uppercase tracking-[0.15em] font-bold text-foreground mb-2">Next steps</p>
                <p className="text-[13px] leading-relaxed text-muted-foreground">
                  Save first, then move from risk map to spread forecast to intervention planning.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to={`/app/risk?scenario=${scenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Risk
                  </Link>
                  <Link to={`/app/forecast?scenario=${scenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Forecast
                  </Link>
                  <Link to={`/app/optimize?scenario=${scenarioId}`} className="border border-border bg-secondary/50 hover:bg-secondary px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-foreground transition-colors">
                    Optimize
                  </Link>
                </div>
              </div>
            ) : null}
          </div>
        </SectionPanel>
      </div>
    </div>
  );
}
