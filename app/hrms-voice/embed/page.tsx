import { VoiceAssistant } from "@/web/components/voice-assistant";

export const dynamic = "force-dynamic";

/**
 * Compact, chrome-free version used by the HRMS corner chat widget. It stays
 * in the existing panel instead of navigating the employee to another page.
 */
export default function HRMSVoiceEmbedPage() {
  return (
    <main className="voice-embed-shell">
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
            startLabel: "Talk by voice",
            demoNote: "Uses your signed-in HRMS identity and existing AI permissions.",
          },
        }}
      />
    </main>
  );
}
