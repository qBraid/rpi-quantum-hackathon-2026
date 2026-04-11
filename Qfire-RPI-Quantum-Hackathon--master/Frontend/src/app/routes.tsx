import { createBrowserRouter } from "react-router";

import { AppShell } from "./components/AppShell";
import { BenchmarkDetailPage } from "./pages/BenchmarkDetailPage";
import { BenchmarksPage } from "./pages/BenchmarksPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForecastPage } from "./pages/ForecastPage";
import { HomePage } from "./pages/HomePage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { LoginPage } from "./pages/LoginPage";
import { OptimizePage } from "./pages/OptimizePage";
import { ReportsPage } from "./pages/ReportsPage";
import { RiskPage } from "./pages/RiskPage";
import { ScenarioWorkspacePage } from "./pages/ScenarioWorkspacePage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { SettingsPage } from "./pages/SettingsPage";

export const router = createBrowserRouter([
  { path: "/", Component: HomePage },
  { path: "/login", Component: LoginPage },
  {
    path: "/app",
    Component: AppShell,
    children: [
      { index: true, Component: DashboardPage },
      { path: "scenarios", Component: ScenariosPage },
      { path: "scenarios/new", Component: ScenarioWorkspacePage },
      { path: "scenarios/:id", Component: ScenarioWorkspacePage },
      { path: "risk", Component: RiskPage },
      { path: "forecast", Component: ForecastPage },
      { path: "optimize", Component: OptimizePage },
      { path: "benchmarks", Component: BenchmarksPage },
      { path: "benchmarks/:id", Component: BenchmarkDetailPage },
      { path: "reports", Component: ReportsPage },
      { path: "integrations", Component: IntegrationsPage },
      { path: "settings", Component: SettingsPage },
    ],
  },
]);
