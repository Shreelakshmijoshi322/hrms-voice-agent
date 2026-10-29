"use client";

import { HRAdminDashboard } from "@/web/components/hr-admin-dashboard";
import { HRDashboard } from "@/web/components/hr-dashboard";
import { DraggableAssistant } from "@/web/components/draggable-assistant";
import { VoiceAssistant, type VoiceAssistantConfig } from "@/web/components/voice-assistant";
import type { DemoRole, DemoSession } from "@/web/lib/demo-users";

function voiceConfigFor(role: DemoRole): VoiceAssistantConfig {
  const shared = {
    tokenEndpoint: "/api/token",
    connectTimeoutMilliseconds: 20_000,
  };
  if (role === "hr_admin") {
    return {
      ...shared,
      panel: {
        eyebrow: "HR voice workspace",
        title: "MY ASSISTANT",
        agentSpeaker: "MY ASSISTANT",
        employeeSpeaker: "You",
        onlineHint: "Ask about workforce data or HR operations.",
        offlineHint: "Start a role-secured HR conversation.",
        suggestions: [
          "Show pending leave requests",
          "ಬಾಕಿ ಇರುವ ರಜೆ ಅರ್ಜಿಗಳನ್ನು ತೋರಿಸಿ",
          "Find Maya Patel",
          "Give me the workforce summary",
          "Search the HR policy library",
        ],
        startLabel: "Talk to HR assistant",
        demoNote: "Fictional HR Admin data and simulated actions",
      },
    };
  }
  return {
    ...shared,
    panel: {
      eyebrow: "Employee voice assistant",
        title: "MY ASSISTANT",
        agentSpeaker: "MY ASSISTANT",
      employeeSpeaker: "You",
        onlineHint: "Speak naturally — MY ASSISTANT waits for your full thought.",
      offlineHint: "Start a private employee self-service conversation.",
      suggestions: [
        "Check my leave balance",
        "ನನ್ನ ರಜೆ ಬಾಕಿ ಎಷ್ಟು ಇದೆ?",
        "Explain Design Weekly Sync",
        "Is Independence Day the next holiday?",
        "What was my July net pay?",
      ],
        startLabel: "Talk to MY ASSISTANT",
      demoNote: "Fictional employee data and simulated actions",
    },
  };
}

export function RoleDashboard({ session }: { session: DemoSession }) {
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    globalThis.location.assign("/login");
  }

  const assistant = (
    <DraggableAssistant>
      <VoiceAssistant config={voiceConfigFor(session.role)} />
    </DraggableAssistant>
  );
  return session.role === "hr_admin" ? (
    <HRAdminDashboard assistant={assistant} onLogout={() => void logout()} session={session} />
  ) : (
    <HRDashboard assistant={assistant} onLogout={() => void logout()} session={session} />
  );
}
