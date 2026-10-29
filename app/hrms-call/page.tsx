import { VoiceAssistant } from "@/web/components/voice-assistant";

export const dynamic = "force-dynamic";

/**
 * Temporary browser-call surface while WhatsApp Calling is waiting for Meta
 * business verification. It deliberately reuses the existing HRMS LiveKit
 * agent and token/session flow.
 */
export default function HRMSCallPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="space-y-3">
        <p className="eyebrow">Temporary browser call</p>
        <h1>Call the HRMS assistant</h1>
        <p className="max-w-2xl text-slate-600">
          Start a secure browser voice call with the existing HRMS agent. Speak
          in English or Kannada and the assistant will answer in the same language.
        </p>
        <p className="max-w-2xl text-sm text-slate-500">
          This is the demo call channel while WhatsApp Calling is pending Meta
          business verification.
        </p>
      </header>
      <VoiceAssistant
        config={{
          tokenEndpoint: "/api/token",
          connectTimeoutMilliseconds: 20_000,
          panel: {
            eyebrow: "Live HRMS call",
            title: "MY ASSISTANT",
            agentSpeaker: "HRMS ASSISTANT",
            employeeSpeaker: "You",
            onlineHint: "You are connected. Ask about leave, payslips, policies, or your profile.",
            offlineHint: "Click start to call the HRMS assistant.",
            suggestions: [
              "Check my leave balance",
              "ನನ್ನ ರಜೆ ಬಾಕಿ ಎಷ್ಟು ಇದೆ?",
              "Get my latest payslip",
              "Explain the remote-work policy",
            ],
            startLabel: "Start HRMS call",
            demoNote: "Uses the existing signed-in HRMS identity and LiveKit voice agent.",
          },
        }}
      />
    </main>
  );
}
