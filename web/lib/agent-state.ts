export type AgentStatusTone =
  | "connecting"
  | "listening"
  | "thinking"
  | "speaking"
  | "muted"
  | "offline"
  | "error";

export type AgentStatusView = {
  label: string;
  tone: AgentStatusTone;
};

export function getAgentStatusView(
  state: string,
  connectionState: string,
  muted: boolean,
): AgentStatusView {
  if (["reconnecting", "signalReconnecting"].includes(connectionState)) {
    return { label: "Reconnecting", tone: "connecting" };
  }
  if (connectionState === "connecting") {
    return { label: "Connecting", tone: "connecting" };
  }
  if (connectionState === "disconnected") {
    return state === "failed"
      ? { label: "Unavailable", tone: "error" }
      : { label: "Offline", tone: "offline" };
  }

  if (muted && !["disconnected", "failed"].includes(state)) {
    return { label: "Muted", tone: "muted" };
  }

  switch (state) {
    case "listening":
      return { label: "Listening", tone: "listening" };
    case "thinking":
      return { label: "Thinking", tone: "thinking" };
    case "speaking":
      return { label: "Speaking", tone: "speaking" };
    case "failed":
      return { label: "Unavailable", tone: "error" };
    case "connecting":
    case "pre-connect-buffering":
    case "initializing":
    case "idle":
      return { label: "Connecting", tone: "connecting" };
    default:
      return { label: "Offline", tone: "offline" };
  }
}
