"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarVisualizer,
  RoomAudioRenderer,
  SessionProvider,
  useAgent,
  useSession,
  useSessionMessages,
} from "@livekit/components-react";
import { TokenSource } from "livekit-client";

import {
  AssistantPanel,
  type AssistantPanelCopy,
  type TranscriptMessage,
} from "@/web/components/assistant-panel";
import { getAgentStatusView } from "@/web/lib/agent-state";

export type VoiceAssistantConfig = {
  tokenEndpoint: string;
  connectTimeoutMilliseconds?: number;
  panel: AssistantPanelCopy;
};

export function VoiceAssistant({ config }: { config: VoiceAssistantConfig }) {
  const tokenSource = useMemo(
    () => TokenSource.endpoint(config.tokenEndpoint),
    [config.tokenEndpoint],
  );
  const session = useSession(tokenSource, {
    agentConnectTimeoutMilliseconds: config.connectTimeoutMilliseconds ?? 15_000,
  });

  return (
    <SessionProvider session={session}>
      <VoiceAssistantContent panelCopy={config.panel} session={session} />
      <RoomAudioRenderer />
    </SessionProvider>
  );
}

type VoiceAssistantContentProps = {
  panelCopy: AssistantPanelCopy;
  session: ReturnType<typeof useSession>;
};

function VoiceAssistantContent({ panelCopy, session }: VoiceAssistantContentProps) {
  const agent = useAgent(session);
  const { messages } = useSessionMessages(session);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const startInFlight = useRef(false);
  const hadConnected = useRef(false);
  const expectedDisconnect = useRef(false);

  useEffect(() => {
    if (session.isConnected) {
      hadConnected.current = true;
      return;
    }
    if (
      session.connectionState === "disconnected" &&
      hadConnected.current &&
      !expectedDisconnect.current
    ) {
      setError("The voice connection ended unexpectedly. Start a new conversation to retry.");
      hadConnected.current = false;
    }
  }, [session.connectionState, session.isConnected]);

  const transcript = useMemo<TranscriptMessage[]>(
    () =>
      messages
        .filter((message) => "message" in message && Boolean(message.message.trim()))
        .map((message) => ({
          id: message.id,
          speaker: message.type === "agentTranscript" ? "agent" : "employee",
          text: "message" in message ? message.message : "",
        })),
    [messages],
  );

  async function start() {
    if (startInFlight.current) return;
    startInFlight.current = true;
    setStarting(true);
    expectedDisconnect.current = false;
    setError(null);
    try {
      await session.start({ tracks: { microphone: { enabled: true } } });
      setMuted(false);
    } catch (caught) {
      const permissionDenied = caught instanceof DOMException && caught.name === "NotAllowedError";
      setError(
        permissionDenied
          ? "Microphone access was blocked. Allow it in your browser settings, then try again."
          : "We couldn’t start the voice assistant. Check your connection and configuration, then retry.",
      );
    } finally {
      startInFlight.current = false;
      setStarting(false);
    }
  }

  async function toggleMute() {
    const nextMuted = !muted;
    try {
      await session.room.localParticipant.setMicrophoneEnabled(!nextMuted);
      setMuted(nextMuted);
    } catch {
      setError("We couldn’t update the microphone. Please retry.");
    }
  }

  async function end() {
    expectedDisconnect.current = true;
    await session.end();
    setMuted(false);
    hadConnected.current = false;
  }

  const status = getAgentStatusView(
    agent.state,
    starting ? "connecting" : session.connectionState,
    muted,
  );

  return (
    <AssistantPanel
      connected={session.isConnected}
      copy={panelCopy}
      error={error ?? (agent.state === "failed" ? agent.failureReasons.join(" ") : null)}
      messages={transcript}
      muted={muted}
      onEnd={() => void end()}
      onStart={() => void start()}
      onToggleMute={() => void toggleMute()}
      starting={starting}
      status={status}
      visualizer={
        agent.microphoneTrack ? (
          <BarVisualizer
            barCount={7}
            state={agent.state}
            track={agent.microphoneTrack}
          />
        ) : undefined
      }
    />
  );
}
