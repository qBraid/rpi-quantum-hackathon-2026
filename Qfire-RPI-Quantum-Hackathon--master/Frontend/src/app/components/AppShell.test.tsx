import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

import { AppShell } from "./AppShell";

vi.mock("../api", () => ({
  api: {
    integrations: vi.fn(async () => ({
      simulator_only: true,
      hardware_available: false,
      qbraid_ready: true,
      providers: [],
    })),
  },
}));

describe("AppShell", () => {
  it("renders workflow navigation and integration banner", async () => {
    render(
      <MemoryRouter initialEntries={["/app/risk"]}>
        <Routes>
          <Route path="/app" element={<AppShell />}>
            <Route path="risk" element={<div>Risk content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getAllByText("QuantumProj").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Risk/i })).toBeInTheDocument();
    expect(screen.getByText("Risk content")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Simulator-only mode/i)).toBeInTheDocument());
  });
});
