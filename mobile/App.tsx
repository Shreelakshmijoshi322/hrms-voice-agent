import { useEffect, useMemo, useState } from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { AudioSession, LiveKitRoom } from "@livekit/react-native";

type Session = { serverUrl: string; token: string; displayName: string };
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://10.0.2.2:3001";
const HRMS_CORE_URL = (process.env.EXPO_PUBLIC_HRMS_CORE_URL ?? "http://10.0.2.2:8081").replace(/\/$/, "");

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speakerOn, setSpeakerOn] = useState(true);
  const redirectUri = useMemo(() => Linking.createURL("auth/callback", { scheme: "hrmsvoicecall" }), []);

  useEffect(() => {
    void (async () => {
      // Prefer the loudspeaker for a hands-free HRMS assistant call. Without
      // an explicit route, some Android devices choose the quiet earpiece.
      await AudioSession.configureAudio({
        android: {
          preferredOutputList: ["speaker", "headset", "bluetooth", "earpiece"],
          audioTypeOptions: {
            audioMode: "inCommunication",
            audioAttributesUsageType: "voiceCommunication",
            audioAttributesContentType: "speech",
            forceHandleAudioRouting: true,
          },
        },
        ios: { defaultOutput: "speaker" },
      });
      await AudioSession.startAudioSession();
      // Android may initialize the voice route below the normal media level.
      // Keep the subscribed agent track at full LiveKit software volume; the
      // user can still control the final loudness with the phone volume keys.
      await AudioSession.setDefaultRemoteAudioTrackVolume(1.0);
      const outputs = await AudioSession.getAudioOutputs();
      if (outputs.includes("speaker")) await AudioSession.selectAudioOutput("speaker");
    })();
    return () => { void AudioSession.stopAudioSession(); };
  }, []);

  async function signInAndStartCall() {
    setBusy(true); setError(null);
    try {
      const authorizeURL = `${HRMS_CORE_URL}/auth/mobile/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`;
      const result = await WebBrowser.openAuthSessionAsync(authorizeURL, redirectUri);
      if (result.type !== "success") throw new Error("HRMS sign-in was cancelled.");
      const callback = Linking.parse(result.url);
      const code = typeof callback.queryParams?.code === "string" ? callback.queryParams.code : "";
      if (!code) throw new Error("HRMS sign-in did not return a valid code.");
      const response = await fetch(`${API_BASE_URL}/api/mobile/token`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }) });
      const body = (await response.json()) as { server_url?: string; participant_token?: string; display_name?: string; error?: string };
      if (!response.ok || !body.server_url || !body.participant_token) throw new Error(body.error ?? "Could not start the HRMS call.");
      setSession({ serverUrl: body.server_url, token: body.participant_token, displayName: body.display_name ?? "HRMS user" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign in to HRMS.");
    } finally { setBusy(false); }
  }

  async function toggleAudioOutput() {
    const nextSpeakerOn = !speakerOn;
    const outputs = await AudioSession.getAudioOutputs();
    const target = nextSpeakerOn ? "speaker" : "earpiece";
    if (outputs.includes(target)) {
      await AudioSession.selectAudioOutput(target);
      setSpeakerOn(nextSpeakerOn);
    }
  }

  if (session) return <SafeAreaView style={styles.container}><LiveKitRoom serverUrl={session.serverUrl} token={session.token} connect audio video={false} options={{ adaptiveStream: true }} onDisconnected={() => setSession(null)}><View style={styles.callCard}><View style={styles.livePill}><View style={styles.liveDot} /><Text style={styles.livePillText}>LIVE HRMS CALL</Text></View><View style={styles.avatar}><Text style={styles.avatarText}>A</Text></View><Text style={styles.callTitle}>Your HR assistant</Text><Text style={styles.status}>Connected as {session.displayName}</Text><Text style={styles.hint}>Speak naturally in English or Kannada. I’m listening.</Text><Pressable style={styles.audioButton} onPress={() => void toggleAudioOutput()}><Text style={styles.audioIcon}>{speakerOn ? "🔊" : "📞"}</Text><Text style={styles.audioText}>{speakerOn ? "Speaker" : "Phone earpiece"}</Text></Pressable><Text style={styles.volumeHint}>Use your phone volume buttons to adjust loudness</Text><Pressable style={styles.endButton} onPress={() => setSession(null)}><Text style={styles.endButtonText}>End call</Text></Pressable></View></LiveKitRoom></SafeAreaView>;

  return <SafeAreaView style={styles.container}><View style={styles.brandRow}><View style={styles.brandMark}><Text style={styles.brandMarkText}>A</Text></View><View><Text style={styles.brand}>AGENTLABS</Text><Text style={styles.brandSub}>HRMS VOICE</Text></View></View><View style={styles.card}><Text style={styles.eyebrow}>YOUR WORKDAY, SIMPLIFIED</Text><Text style={styles.title}>Talk to your HR assistant</Text><Text style={styles.subtitle}>Ask about leave, attendance, payslips, holidays, or employee information using your voice.</Text><View style={styles.languageRow}><Text style={styles.language}>EN</Text><Text style={styles.language}>ಕನ್ನಡ</Text><Text style={styles.languageHint}>English + Kannada</Text></View>{error ? <Text style={styles.error}>{error}</Text> : null}<Pressable disabled={busy} style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]} onPress={() => void signInAndStartCall()}><Text style={styles.buttonText}>{busy ? "Connecting…" : "Sign in and start call"}</Text><Text style={styles.buttonArrow}>→</Text></Pressable><Text style={styles.note}>Secure sign-in · Your password never enters this app</Text></View><Text style={styles.footer}>Powered by AgentLabs HRMS</Text></SafeAreaView>;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0b1020", justifyContent: "center", padding: 22 },
  brandRow: { alignItems: "center", flexDirection: "row", gap: 12, marginBottom: 24, paddingHorizontal: 4 },
  brandMark: { alignItems: "center", backgroundColor: "#6c63ff", borderRadius: 14, height: 46, justifyContent: "center", width: 46 },
  brandMarkText: { color: "#ffffff", fontSize: 25, fontWeight: "900" },
  brand: { color: "#ffffff", fontSize: 15, fontWeight: "900", letterSpacing: 2 },
  brandSub: { color: "#8993b8", fontSize: 10, fontWeight: "700", letterSpacing: 1.5, marginTop: 2 },
  card: { backgroundColor: "#151d34", borderColor: "#263252", borderRadius: 26, borderWidth: 1, padding: 26, gap: 17 },
  callCard: { flex: 1, backgroundColor: "#11182e", borderRadius: 26, justifyContent: "center", alignItems: "center", padding: 28, gap: 18 },
  livePill: { alignItems: "center", backgroundColor: "#1c2940", borderRadius: 20, flexDirection: "row", gap: 8, paddingHorizontal: 13, paddingVertical: 8 },
  liveDot: { backgroundColor: "#40e0a0", borderRadius: 5, height: 10, width: 10 },
  livePillText: { color: "#a9b5d5", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  avatar: { alignItems: "center", backgroundColor: "#6c63ff", borderColor: "#9c95ff", borderRadius: 55, borderWidth: 5, height: 110, justifyContent: "center", marginTop: 18, width: 110 },
  avatarText: { color: "#ffffff", fontSize: 54, fontWeight: "800" },
  eyebrow: { color: "#938cff", fontSize: 11, fontWeight: "800", letterSpacing: 1.6 },
  title: { color: "#ffffff", fontSize: 30, fontWeight: "800", lineHeight: 36 },
  callTitle: { color: "#ffffff", fontSize: 30, fontWeight: "800" },
  subtitle: { color: "#a7b1cc", fontSize: 15, lineHeight: 23 },
  languageRow: { alignItems: "center", flexDirection: "row", gap: 8 },
  language: { backgroundColor: "#252e4b", borderRadius: 7, color: "#d9ddff", fontSize: 11, fontWeight: "800", overflow: "hidden", paddingHorizontal: 9, paddingVertical: 6 },
  languageHint: { color: "#7783a5", fontSize: 12, marginLeft: 3 },
  status: { color: "#aeb8ff", fontSize: 15 },
  hint: { color: "#dfe3ff", fontSize: 17, lineHeight: 25, textAlign: "center" },
  audioButton: { alignItems: "center", backgroundColor: "#222d4b", borderColor: "#3b4a70", borderRadius: 13, borderWidth: 1, flexDirection: "row", gap: 9, paddingHorizontal: 18, paddingVertical: 12 },
  audioIcon: { fontSize: 18 },
  audioText: { color: "#dfe3ff", fontSize: 14, fontWeight: "700" },
  volumeHint: { color: "#7783a5", fontSize: 11, marginTop: -8 },
  button: { alignItems: "center", backgroundColor: "#6c63ff", borderRadius: 13, flexDirection: "row", justifyContent: "center", padding: 16 },
  buttonPressed: { backgroundColor: "#554cf0" },
  buttonText: { color: "#ffffff", fontSize: 15, fontWeight: "800" },
  buttonArrow: { color: "#ffffff", fontSize: 22, fontWeight: "400", marginLeft: 10 },
  endButton: { backgroundColor: "#e05d72", borderRadius: 13, paddingHorizontal: 30, paddingVertical: 15 },
  endButtonText: { color: "#ffffff", fontWeight: "700" },
  error: { backgroundColor: "#3a2037", borderRadius: 9, color: "#ff9eae", fontSize: 13, padding: 10 },
  note: { color: "#6f7c9f", fontSize: 11, textAlign: "center" },
  footer: { color: "#4f5b7c", fontSize: 11, marginTop: 22, textAlign: "center" },
});
