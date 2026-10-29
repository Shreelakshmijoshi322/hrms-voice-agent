import type { ReactNode } from "react";
import { Headphones, Mic, MicOff, PhoneOff, ShieldCheck, Sparkles } from "lucide-react";

import type { AgentStatusView } from "@/web/lib/agent-state";

export type TranscriptMessage = {
  id: string;
  speaker: "employee" | "agent";
  text: string;
};

type AssistantPanelProps = {
  connected: boolean;
  copy: AssistantPanelCopy;
  error?: string | null;
  messages: TranscriptMessage[];
  muted: boolean;
  onEnd: () => void;
  onStart: () => void;
  onToggleMute: () => void;
  starting?: boolean;
  status: AgentStatusView;
  visualizer?: ReactNode;
};

export type AssistantPanelCopy = {
  eyebrow: string;
  title: string;
  agentSpeaker: string;
  employeeSpeaker: string;
  onlineHint: string;
  offlineHint: string;
  suggestions: string[];
  startLabel: string;
  demoNote: string;
};

export function AssistantPanel({
  connected,
  copy,
  error,
  messages,
  muted,
  onEnd,
  onStart,
  onToggleMute,
  starting = false,
  status,
  visualizer,
}: AssistantPanelProps) {
  return (
    <section className="assistant-panel" aria-labelledby="assistant-title">
      <div className="assistant-head">
        <div className="assistant-mark" aria-hidden="true">
          <Sparkles size={19} />
        </div>
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="assistant-title">{copy.title}</h2>
        </div>
        <span className={`status-pill status-${status.tone}`}>
          <span className="status-dot" aria-hidden="true" />
          {status.label}
        </span>
      </div>

      {error ? <p className="assistant-error" role="alert">{error}</p> : null}

      <div className="transcript" aria-label="Conversation transcript" aria-live="polite">
        {messages.length === 0 ? (
          <div className="transcript-empty">
            <p>Quick questions</p>
            <div className="suggestion-list">
              {copy.suggestions.map((suggestion) => (
                <span key={suggestion}>{suggestion}</span>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div className={`message message-${message.speaker}`} key={message.id}>
              <span>{message.speaker === "agent" ? copy.agentSpeaker : copy.employeeSpeaker}</span>
              <p>{message.text}</p>
            </div>
          ))
        )}
      </div>

      <div className="voice-footer">
        <div className="voice-stage">
          <div className={`voice-orb voice-orb-${status.tone}`} aria-hidden="true">
            <Headphones size={30} />
          </div>
          <div className="waveform" aria-label={`${status.label} audio visualization`}>
            {visualizer ??
              [12, 24, 36, 20, 30, 16, 26].map((height, index) => (
                <span key={index} style={{ height }} />
              ))}
          </div>
          <p className="voice-hint">
            {starting
              ? "Connecting…"
              : connected
                ? status.tone === "listening"
                  ? "Listening…"
                  : status.tone === "thinking"
                    ? "Thinking…"
                    : status.tone === "speaking"
                      ? "Speaking…"
                      : status.label
                : "Tap to speak"}
          </p>
        </div>

        <div className="voice-controls">
          {connected ? (
            <>
              <button
                className="icon-control"
                onClick={onToggleMute}
                type="button"
                aria-label={muted ? "Unmute microphone" : "Mute microphone"}
                title={muted ? "Unmute microphone" : "Mute microphone"}
              >
                {muted ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <button className="end-control" onClick={onEnd} type="button" aria-label="End conversation">
                <PhoneOff size={18} />
                End
              </button>
            </>
          ) : (
            <button
              className="start-control"
              disabled={starting}
              onClick={onStart}
              type="button"
              aria-label={copy.startLabel}
            >
              <Mic size={19} />
              {starting ? "Connecting…" : copy.startLabel}
            </button>
          )}
        </div>

        <p className="demo-note"><ShieldCheck size={14} /> {copy.demoNote}</p>
      </div>
    </section>
  );
}
