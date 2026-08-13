import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HRDashboard } from "@/web/components/hr-dashboard";

describe("HRDashboard", () => {
  it("presents a recognizable HRMS employee overview", () => {
    render(<HRDashboard assistant={<aside>Voice assistant</aside>} />);

    expect(screen.getByRole("heading", { name: "Maya Patel" })).toBeInTheDocument();
    expect(screen.getByText(/Product Designer/)).toBeInTheDocument();
    expect(screen.getByText("12 days")).toBeInTheDocument();
    expect(screen.getByText("July 2026")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByText("Voice assistant")).toBeInTheDocument();
  });
});
