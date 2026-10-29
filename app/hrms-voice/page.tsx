import { VoiceAssistant } from "@/web/components/voice-assistant";

export const dynamic = "force-dynamic";

export default function HRMSVoicePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="space-y-3">
        <p className="eyebrow">AgentLabs HRMS</p>
        <h1>Talk to MY ASSISTANT</h1>
        <p className="max-w-2xl text-slate-600">
          Your voice request is routed through LiveKit to the authenticated HRMS AI agent.
        </p>
      </header>
      <VoiceAssistant
        config={{
          tokenEndpoint: "/api/token",
          connectTimeoutMilliseconds: 20_000,
          panel: {
            eyebrow: "HRMS voice assistant",
            title: "MY ASSISTANT",
            agentSpeaker: "MY ASSISTANT",
            employeeSpeaker: "You",
            onlineHint: "Ask about your leave, payslips, policies, and profile.",
            offlineHint: "Start a secure HRMS voice conversation.",
            suggestions: [
              "Check my leave balance",
              "ನನ್ನ ರಜೆ ಬಾಕಿ ಎಷ್ಟು ಇದೆ?",
              "Get my latest payslip",
              "Explain the remote-work policy",
              "Request leave for next Friday",
            ],
            startLabel: "Talk to HR assistant",
            demoNote: "Voice requests use the signed-in HRMS identity and existing AI permissions.",
          },
        }}
      />
    </main>
  );
}
