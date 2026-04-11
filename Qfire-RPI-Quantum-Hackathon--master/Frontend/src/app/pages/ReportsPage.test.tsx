import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import { ReportsPage } from "./ReportsPage";

const { generateReport } = vi.hoisted(() => ({
  generateReport: vi.fn(async () => ({
    id: "report-1",
    scenario_id: "scenario-1",
    title: "Wildfire decision report",
    status: "complete",
    sections: {
      executive_summary: ["Summary line"],
      methodology: ["Method line"],
      risk: { recommended_mode: "hybrid" },
      forecast: { containment_outlook: "manageable" },
      optimization: { recommended_mode: "hybrid" },
      benchmark_detail: { best_strategy: "qbraid_target_aware_bridge" },
    },
    export: { content: "# report", filename: "report.md" },
    created_at: "2026-04-10T12:00:00Z",
  })),
}));

vi.mock("../api", () => ({
  api: {
    listScenarios: vi.fn(async () => [
      { id: "scenario-1", name: "Scenario A" },
    ]),
    listReports: vi.fn(async () => []),
    listRiskRuns: vi.fn(async () => [{ id: "risk-1", created_at: "2026-04-10T12:00:00Z" }]),
    listForecastRuns: vi.fn(async () => [{ id: "forecast-1", created_at: "2026-04-10T12:00:00Z" }]),
    listOptimizeRuns: vi.fn(async () => [{ id: "opt-1", created_at: "2026-04-10T12:00:00Z" }]),
    listBenchmarks: vi.fn(async () => [{ id: "bench-1", created_at: "2026-04-10T12:00:00Z" }]),
    generateReport,
  },
}));

describe("ReportsPage", () => {
  it("uses explicit run selections when generating a report", async () => {
    render(
      <MemoryRouter initialEntries={["/app/reports?scenario=scenario-1&risk=risk-1"]}>
        <ReportsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("Decision reports")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Generate report/i }));

    await waitFor(() => expect(generateReport).toHaveBeenCalled());
    expect(generateReport).toHaveBeenCalledWith(
      expect.objectContaining({
        scenario_id: "scenario-1",
        risk_run_id: "risk-1",
      }),
    );
    await waitFor(() => expect(screen.getByText("Wildfire decision report")).toBeInTheDocument());
  });
});
