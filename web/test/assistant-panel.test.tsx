import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssistantPanel } from "@/web/components/assistant-panel";

const copy = {
  eyebrow: "Voice assistant",
  title: "Ask People",
  agentSpeaker: "Ask People",
  employeeSpeaker: "You",
  onlineHint: "Speak naturally.",
  offlineHint: "Get instant help.",
  suggestions: ["Check my leave balance"],
  startLabel: "Talk to HR assistant",
  demoNote: "Simulated HRMS demo",
};

describe("AssistantPanel", () => {
  it("renders state, transcript, and active voice controls", () => {
    const onToggleMute = vi.fn();
    const onEnd = vi.fn();

    render(
      <AssistantPanel
        connected
        copy={copy}
        muted={false}
        onEnd={onEnd}
        onStart={vi.fn()}
        onToggleMute={onToggleMute}
        status={{ label: "Listening", tone: "listening" }}
        messages={[
          { id: "1", speaker: "employee", text: "How much leave do I have?" },
          { id: "2", speaker: "agent", text: "You have 12 vacation days." },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Ask People" })).toBeInTheDocument();
    expect(screen.getByText("Listening")).toBeInTheDocument();
    expect(screen.getByText("You have 12 vacation days.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mute microphone" }));
    fireEvent.click(screen.getByRole("button", { name: "End conversation" }));

    expect(onToggleMute).toHaveBeenCalledOnce();
    expect(onEnd).toHaveBeenCalledOnce();
  });

  it("starts only after the employee chooses to talk", () => {
    const onStart = vi.fn();
    render(
      <AssistantPanel
        connected={false}
        copy={copy}
        messages={[]}
        muted={false}
        onEnd={vi.fn()}
        onStart={onStart}
        onToggleMute={vi.fn()}
        status={{ label: "Offline", tone: "offline" }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Talk to HR assistant" }));

    expect(onStart).toHaveBeenCalledOnce();
    expect(screen.getByText("Simulated HRMS demo")).toBeInTheDocument();
  });

  it("prevents another start while a connection is in flight", () => {
    const onStart = vi.fn();
    render(
      <AssistantPanel
        connected={false}
        copy={copy}
        messages={[]}
        muted={false}
        onEnd={vi.fn()}
        onStart={onStart}
        onToggleMute={vi.fn()}
        starting
        status={{ label: "Connecting", tone: "connecting" }}
      />,
    );

    const button = screen.getByRole("button", { name: "Talk to HR assistant" });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onStart).not.toHaveBeenCalled();
  });
});
