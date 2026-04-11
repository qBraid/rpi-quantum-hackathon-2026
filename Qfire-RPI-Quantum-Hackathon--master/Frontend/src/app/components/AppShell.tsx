import { useMemo } from "react";
import { Link, Outlet, useLocation } from "react-router";
import {
  Atom,
  Cpu,
  LayoutDashboard,
  Layers,
  Target,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

import { api } from "../api";
import { SimulatorBanner, StatusPill, cx } from "./product";
import { useAsyncData } from "../useAsyncData";

const navItems = [
  { path: "/app", label: "Overview", icon: LayoutDashboard },
  { path: "/app/scenarios", label: "Scenarios", icon: Layers },
  { path: "/app/risk", label: "Risk Map", icon: AlertTriangle },
  { path: "/app/forecast", label: "Spread Forecast", icon: TrendingUp },
  { path: "/app/optimize", label: "Intervention Plan", icon: Target },
  { path: "/app/benchmarks", label: "Benchmark Integrity", icon: Cpu },
];

export function AppShell() {
  const location = useLocation();
  const { data: integrations } = useAsyncData(api.integrations, []);

  const activeLabel = useMemo(
    () => navItems.find((item) => location.pathname === item.path || location.pathname.startsWith(`${item.path}/`))?.label ?? "Workspace",
    [location.pathname],
  );

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <div className="mx-auto flex min-h-screen 2xl:max-w-[1800px] border-x border-border shadow-2xl bg-white">
        <aside className="hidden w-[280px] shrink-0 border-r border-border bg-card px-6 py-8 text-foreground lg:flex lg:flex-col relative z-10">
          <div className="flex items-center gap-3 mb-10">
            <div className="flex h-10 w-10 items-center justify-center rounded-none bg-primary text-primary-foreground">
              <Atom className="h-5 w-5 text-qp-cyan" />
            </div>
            <div>
              <p className="text-[16px] font-bold tracking-tight">QuantumProj</p>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground mt-0.5">Decision Intelligence</p>
            </div>
          </div>

          <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Workflow</p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cx(
                    "flex items-center gap-3 border-l-2 px-4 py-2.5 text-[13px] font-medium transition-all duration-200",
                    active ? "border-primary bg-secondary/50 text-foreground" : "border-transparent text-muted-foreground hover:bg-secondary/20 hover:text-foreground",
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col bg-[#fdfdfc]">
          <header className="sticky top-0 z-20 border-b border-border bg-white/95 px-6 py-5 backdrop-blur-md lg:px-10">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <nav className="flex text-[11px] font-bold uppercase tracking-[0.15em] text-muted-foreground mb-1.5 space-x-2">
                  <span>QuantumProj</span>
                  <span>/</span>
                  <span className="text-foreground">{activeLabel}</span>
                </nav>
              </div>
              <div className="flex flex-1 items-center gap-4 lg:justify-end">
                {integrations ? (
                  <StatusPill label={integrations.simulator_only ? "Simulator only" : "Hardware ready"} tone={integrations.simulator_only ? "warn" : "good"} />
                ) : null}
              </div>
            </div>
          </header>

          <main className="flex-1 px-6 py-8 lg:px-10">
            {integrations ? (
              <div className="mb-8">
                <SimulatorBanner simulatorOnly={integrations.simulator_only} qbraidReady={integrations.qbraid_ready} />
              </div>
            ) : null}
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
