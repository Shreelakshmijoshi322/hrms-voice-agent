import { describe, expect, it } from "vitest";

import { getAgentStatusView } from "@/web/lib/agent-state";

describe("getAgentStatusView", () => {
  it.each([
    ["connecting", "Connecting", "connecting"],
    ["listening", "Listening", "listening"],
    ["thinking", "Thinking", "thinking"],
    ["speaking", "Speaking", "speaking"],
    ["disconnected", "Offline", "offline"],
  ] as const)("maps %s to a user-facing state", (state, label, tone) => {
    expect(getAgentStatusView(state, "connected", false)).toEqual({ label, tone });
  });

  it("shows muted while a connected microphone is muted", () => {
    expect(getAgentStatusView("listening", "connected", true)).toEqual({
      label: "Muted",
      tone: "muted",
    });
  });

  it.each(["reconnecting", "signalReconnecting"])(
    "shows recovery while the room is %s",
    (connectionState) => {
      expect(getAgentStatusView("listening", connectionState, false)).toEqual({
        label: "Reconnecting",
        tone: "connecting",
      });
    },
  );

  it("does not keep showing listening after the room disconnects", () => {
    expect(getAgentStatusView("listening", "disconnected", false)).toEqual({
      label: "Offline",
      tone: "offline",
    });
  });
});
