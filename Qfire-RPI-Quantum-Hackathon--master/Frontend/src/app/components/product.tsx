import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { toast } from "sonner";

import type { CellState } from "../types";

const stateStyles: Record<CellState, string> = {
  empty: "bg-card border-border",
  road_or_firebreak: "bg-[#e4e4e7] border-[#d4d4d8]",
  dry_brush: "bg-[#fde68a] border-[#fcd34d]",
  grass: "bg-[#d9f99d] border-[#bef264]",
  shrub: "bg-[#a3e635] border-[#84cc16]",
  tree: "bg-[#4d7c0f] border-[#3f6212]",
  water: "bg-[#0ea5e9] border-[#0284c7]",
  protected: "bg-[#818cf8] border-[#6366f1]",
  intervention: "bg-[#ffedd5] border-[#ea580c]",
  ignition: "bg-[#ef4444] border-[#dc2626]",
  burned: "bg-[#18181b] border-[#09090b]",
};

const stateLabels: Record<CellState, string> = {
  empty: "Empty",
  road_or_firebreak: "Road / Firebreak",
  dry_brush: "Dry Brush",
  grass: "Grass",
  shrub: "Shrub",
  tree: "Tree",
  water: "Water",
  protected: "Protected",
  intervention: "Intervention",
  ignition: "Ignition",
  burned: "Burned",
};

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function toastSuccess(message: string, description?: string) {
  toast.success(message, { description });
}

export function toastError(message: string, description?: string) {
  toast.error(message, { description });
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between pb-8 border-b border-border">
      <div className="max-w-3xl">
        {eyebrow ? <p className="mb-3 text-[12px] font-bold uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</p> : null}
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? <p className="mt-4 text-[15px] font-normal leading-relaxed text-muted-foreground border-l-2 border-primary pl-4">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
    </div>
  );
}

export function SectionPanel({
  title,
  subtitle,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("border border-border bg-card flex flex-col", className)}>
      {title ? (
        <div className="flex flex-col border-b border-border bg-secondary/30 px-6 py-4">
          <h2 className="text-[16px] font-semibold tracking-tight text-foreground">{title}</h2>
          {subtitle ? <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{subtitle}</p> : null}
        </div>
      ) : null}
      <div className="p-6 grow flex flex-col">
        {children}
      </div>
    </section>
  );
}

export function MetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="border border-border bg-card p-5 transition-colors hover:border-primary/50">
      <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground">{label}</p>
      <p className="mt-3 text-[32px] font-light tracking-tight text-foreground">{value}</p>
      {hint ? <p className="mt-2 text-[12px] font-medium text-muted-foreground border-t border-border pt-2">{hint}</p> : null}
    </div>
  );
}

export function StatusPill({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "good" | "warn" | "accent" }) {
  const toneClass =
    tone === "good"
      ? "bg-emerald-50 text-emerald-700"
      : tone === "warn"
      ? "bg-amber-50 text-amber-700"
      : tone === "accent"
        ? "bg-cyan-50 text-cyan-700"
        : "bg-secondary text-foreground";
  return <span className={cx("inline-flex border border-border px-3 py-1 text-[11px] font-bold uppercase tracking-wider", toneClass)}>{label}</span>;
}

export function Notice({
  tone = "info",
  title,
  description,
}: {
  tone?: "info" | "success" | "warn" | "error";
  title: string;
  description: string;
}) {
  const styles =
    tone === "success"
      ? {
          wrap: "border-emerald-500",
          icon: <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />,
        }
      : tone === "warn"
        ? {
            wrap: "border-amber-500",
            icon: <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />,
          }
        : tone === "error"
          ? {
              wrap: "border-red-500",
              icon: <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />,
            }
          : {
              wrap: "border-cyan-500",
              icon: <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-cyan-500" />,
            };
  return (
    <div className={cx("border-l-4 p-4 text-[13px] bg-card", styles.wrap)}>
      <div className="flex items-start gap-4">
        {styles.icon}
        <div>
          <p className="font-semibold uppercase tracking-wide text-[11px] mb-1">{title}</p>
          <p className="leading-relaxed text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  );
}

export function SimulatorBanner({ simulatorOnly, qbraidReady }: { simulatorOnly: boolean; qbraidReady: boolean }) {
  if (!simulatorOnly && qbraidReady) {
    return null;
  }
  return (
    <Notice
      tone="warn"
      title="Simulator-only mode"
      description={
        !qbraidReady
          ? "IBM hardware execution is unavailable and qBraid or Qiskit readiness is incomplete. Benchmark outputs stay honest and degraded states are labeled explicitly."
          : "IBM hardware execution is unavailable. The workflow stays usable through simulator-backed execution and the UI labels hardware availability clearly."
      }
    />
  );
}

export function LoadingState({ label = "Loading workspace data..." }: { label?: string }) {
  return (
    <div className="flex min-h-[200px] items-center justify-center rounded-2xl border border-dashed border-border bg-card/50">
      <div className="flex items-center gap-3 text-[13px] text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>{label}</span>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/60 px-6 text-center">
      <AlertTriangle className="h-6 w-6 text-qp-cyan" />
      <h3 className="mt-4 text-[16px] font-semibold text-foreground">{title}</h3>
      <p className="mt-2 max-w-md text-[13px] leading-6 text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ScenarioGrid({
  grid,
  selected,
  onSelect,
  editable = false,
  brushState,
  scoreLookup,
  interventionLookup,
  differenceLookup,
}: {
  grid: CellState[][];
  selected?: [number, number] | null;
  onSelect?: (row: number, col: number) => void;
  editable?: boolean;
  brushState?: CellState;
  scoreLookup?: Record<string, number>;
  interventionLookup?: Record<string, boolean>;
  differenceLookup?: Record<string, "protected" | "changed">;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="grid grid-cols-10 gap-px bg-border p-px">
        {grid.map((row, rowIndex) =>
          row.map((cell, colIndex) => {
            const score = scoreLookup?.[`${rowIndex}-${colIndex}`];
            const interventionMarked = cell === "intervention" || Boolean(interventionLookup?.[`${rowIndex}-${colIndex}`]);
            const difference = differenceLookup?.[`${rowIndex}-${colIndex}`];
            const isSelected = selected?.[0] === rowIndex && selected?.[1] === colIndex;
            return (
              <button
                key={`${rowIndex}-${colIndex}`}
                type="button"
                onClick={() => onSelect?.(rowIndex, colIndex)}
                className={cx(
                  "relative aspect-square transition-all duration-200",
                  stateStyles[cell],
                  editable ? "cursor-pointer hover:border-qp-cyan hover:z-10" : "cursor-default",
                  isSelected && "ring-2 ring-qp-cyan ring-offset-2 z-20",
                )}
                title={`${rowIndex},${colIndex} - ${stateLabels[cell]}${brushState && editable ? ` -> ${stateLabels[brushState]}` : ""}`}
              >
                {interventionMarked ? (
                  <>
                    <div className="absolute inset-[2px] border-2 border-[#c2410c] bg-[repeating-linear-gradient(135deg,rgba(249,115,22,0.18),rgba(249,115,22,0.18)_4px,transparent_4px,transparent_8px)]" />
                    <div className="absolute inset-0 flex items-center justify-center text-[9px] font-black uppercase tracking-[0.18em] text-[#9a3412]">T</div>
                  </>
                ) : null}
                {difference ? (
                  <div
                    className={cx(
                      "absolute inset-[1px] border-2",
                      difference === "protected" ? "border-cyan-300 bg-cyan-400/10" : "border-white/70 bg-white/10",
                    )}
                  />
                ) : null}
                {typeof score === "number" ? (
                  <div className="absolute inset-x-0 bottom-0 bg-black/60 p-0.5 text-center text-[10px] font-bold tracking-wider text-white backdrop-blur-sm">
                    {(score * 100).toFixed(0)}
                  </div>
                ) : null}
              </button>
            );
          }),
        )}
      </div>
      <div className="mt-6 flex flex-wrap gap-x-4 gap-y-2">
        {(Object.entries(stateStyles) as [CellState, string][]).map(([state, cls]) => (
          <div key={state} className="flex items-center gap-2">
            <div className={cx("relative h-3 w-3 border", cls)}>
              {state === "intervention" ? <div className="absolute inset-0 bg-[repeating-linear-gradient(135deg,rgba(249,115,22,0.5),rgba(249,115,22,0.5)_2px,transparent_2px,transparent_4px)]" /> : null}
            </div>
            <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted-foreground">{stateLabels[state]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
