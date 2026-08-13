import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RoleDashboard } from "@/web/components/role-dashboard";
import type { DemoSession } from "@/web/lib/demo-users";

vi.mock("@/web/components/voice-assistant", () => ({
  VoiceAssistant: ({ config }: { config: { panel: { suggestions: string[] } } }) => (
    <aside aria-label="Voice assistant">
      {config.panel.suggestions.map((suggestion) => (
        <span key={suggestion}>{suggestion}</span>
      ))}
    </aside>
  ),
}));

const employeeSession: DemoSession = {
  userId: "EMP-1042",
  role: "employee",
  name: "Maya Patel",
  email: "maya@people.demo",
};

const hrSession: DemoSession = {
  userId: "HR-2001",
  role: "hr_admin",
  name: "Priya Sharma",
  email: "priya@people.demo",
};

describe("RoleDashboard", () => {
  it("renders employee content and prompts", () => {
    render(<RoleDashboard session={employeeSession} />);

    expect(screen.getByText("12 days")).toBeInTheDocument();
    expect(screen.getByText("Explain Design Weekly Sync")).toBeInTheDocument();
    expect(screen.queryByText("Leave approvals")).not.toBeInTheDocument();
  });

  it("renders HR workforce and approval content", () => {
    render(<RoleDashboard session={hrSession} />);

    expect(screen.getByText("248")).toBeInTheDocument();
    expect(screen.getByText("Leave approvals")).toBeInTheDocument();
    expect(screen.getByText("Show pending leave requests")).toBeInTheDocument();
  });
});
