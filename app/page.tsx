import { HRDashboard } from "@/web/components/hr-dashboard";
import { VoiceAssistant } from "@/web/components/voice-assistant";

export default function HomePage() {
  return (
    <HRDashboard
      assistant={
        <VoiceAssistant
          config={{
            tokenEndpoint: "/api/token",
            panel: {
              eyebrow: "Voice assistant",
              title: "Ask People",
              agentSpeaker: "Ask People",
              employeeSpeaker: "You",
              onlineHint: "Speak naturally — you can interrupt anytime.",
              offlineHint: "Get instant help with everyday HR tasks.",
              suggestions: [
                "Check my leave balance",
                "Explain remote-work policy",
                "When was my latest payslip?",
              ],
              startLabel: "Talk to HR assistant",
              demoNote: "Simulated HRMS demo",
            },
          }}
        />
      }
    />
  );
}
