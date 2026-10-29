"use client";

import { FormEvent, useState } from "react";

type TestResult = {
  replyText?: string;
  mode?: string;
  duplicate?: boolean;
  error?: string;
};

export default function WhatsAppTestPage() {
  const [message, setMessage] = useState("");
  const [kind, setKind] = useState<"text" | "audio">("text");
  const [result, setResult] = useState<TestResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function sendTest(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const response = await fetch("/api/whatsapp/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: kind, text: message }),
      });
      const payload = (await response.json()) as TestResult;
      setResult(response.ok ? payload : { error: payload.error || "Request failed" });
    } catch {
      setResult({ error: "The local test request failed." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", background: "#f5f7fb", padding: "48px 20px", color: "#172033" }}>
      <section style={{ maxWidth: 720, margin: "0 auto", background: "white", borderRadius: 20, padding: 32, boxShadow: "0 14px 40px #15213b14" }}>
        <p style={{ color: "#5267d9", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase", fontSize: 12 }}>HRMS WhatsApp integration</p>
        <h1 style={{ margin: "8px 0 10px", fontSize: 32 }}>Local WhatsApp test</h1>
        <p style={{ color: "#5b6578", lineHeight: 1.6 }}>
          This local page tests the webhook and message-processing boundary while Meta approval is pending. It does not send a real WhatsApp message.
        </p>
        <form onSubmit={sendTest} style={{ display: "grid", gap: 16, marginTop: 24 }}>
          <label style={{ display: "grid", gap: 8, fontWeight: 700 }}>
            Message type
            <select value={kind} onChange={(event) => setKind(event.target.value as "text" | "audio")} style={{ padding: 12, border: "1px solid #d9deea", borderRadius: 10, fontSize: 15 }}>
              <option value="text">Text message</option>
              <option value="audio">Voice message</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 8, fontWeight: 700 }}>
            Text or transcript for the mock
            <textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Try: What is my leave balance?" rows={4} disabled={kind === "audio"} style={{ padding: 12, border: "1px solid #d9deea", borderRadius: 10, fontSize: 15, resize: "vertical" }} />
          </label>
          <button type="submit" disabled={busy} style={{ border: 0, borderRadius: 10, padding: "13px 18px", background: busy ? "#9aa5c5" : "#5267d9", color: "white", fontWeight: 700, cursor: busy ? "wait" : "pointer" }}>
            {busy ? "Processing…" : "Send local test"}
          </button>
        </form>
        {result && (
          <div style={{ marginTop: 24, borderRadius: 12, background: result.error ? "#fff0f0" : "#eef8f1", padding: 16 }}>
            <strong>{result.error ? "Error" : "Agent response"}</strong>
            <p style={{ marginBottom: 0, lineHeight: 1.6 }}>{result.error || result.replyText}</p>
            {!result.error && <small>Mode: {result.mode}</small>}
          </div>
        )}
      </section>
    </main>
  );
}
