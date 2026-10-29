"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarVisualizer,
  RoomAudioRenderer,
  SessionProvider,
  useAgent,
  useLocalParticipant,
  useSession,
  useSessionMessages,
} from "@livekit/components-react";
import { TokenSource, type AudioCaptureOptions } from "livekit-client";

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

// Prefer a close, single-channel speech signal. Disabling automatic gain
// control is intentional here: AGC can amplify a distant speaker until they
// are louder than the person near the microphone. voiceIsolation is an
// experimental browser constraint, so unsupported browsers simply ignore it.
const MICROPHONE_CAPTURE_OPTIONS: AudioCaptureOptions = {
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: false,
  voiceIsolation: true,
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
  const {
    isMicrophoneEnabled,
    lastMicrophoneError,
    localParticipant,
  } = useLocalParticipant({ room: session.room });
  const { messages } = useSessionMessages(session);
  const [muted, setMuted] = useState(true);
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
      await session.start({
        tracks: {
          microphone: {
            // Capture explicitly below so browser audio constraints are
            // applied instead of relying on the browser's default AGC.
            enabled: false,
          },
        },
      });
      // Keep the microphone closed until the user explicitly unmutes it. This
      // prevents nearby and distant conversations from entering the call.
      setMuted(true);
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
    try {
      await session.room.localParticipant.setMicrophoneEnabled(
        muted,
        muted ? MICROPHONE_CAPTURE_OPTIONS : undefined,
      );
      setMuted(!muted);
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
    muted || (session.isConnected && !isMicrophoneEnabled),
  );

  const microphoneError = lastMicrophoneError
    ? "Microphone access failed. Allow microphone access for localhost and start again."
    : session.isConnected && !starting && !muted && !isMicrophoneEnabled
      ? "The room is connected, but your microphone is not active. Click the microphone button to retry."
      : null;

  return (
    <AssistantPanel
      connected={session.isConnected}
      copy={panelCopy}
      error={
        error ??
        microphoneError ??
        (agent.state === "failed" ? agent.failureReasons.join(" ") : null)
      }
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
