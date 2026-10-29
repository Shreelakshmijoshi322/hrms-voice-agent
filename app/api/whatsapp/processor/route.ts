import { NextResponse } from "next/server";

import { sarvamSpeechToText, sarvamTextToSpeech } from "@/web/lib/sarvam";

export const runtime = "nodejs";

/**
 * Internal boundary for WhatsApp audio. The HRMS answer service is deliberately
 * separate because the existing LiveKit worker owns authenticated room sessions.
 * It must return { answer: string } and receive { from, transcript, languageCode }.
 */
export async function POST(request: Request) {
  const agentUrl = process.env.WHATSAPP_HRMS_AGENT_URL?.trim();
  if (!agentUrl) {
    return NextResponse.json(
      { error: "WHATSAPP_HRMS_AGENT_URL is not configured." },
      { status: 503 },
    );
  }

  const contentType = request.headers.get("content-type") || "";
  let from = "";
  let transcript: { transcript: string; languageCode: string };

  if (contentType.includes("multipart/form-data") || contentType.includes("application/x-www-form-urlencoded")) {
    const form = await request.formData();
    const file = form.get("file");
    from = String(form.get("from") || "").trim();
    if (!(file instanceof File) || !from) {
      return NextResponse.json({ error: "file and from are required" }, { status: 400 });
    }
    transcript = await sarvamSpeechToText(file);
  } else {
    const body = (await request.json().catch(() => null)) as { from?: string; text?: string } | null;
    from = String(body?.from || "").trim();
    const text = String(body?.text || "").trim();
    if (!from || !text) {
      return NextResponse.json({ error: "JSON requests require from and text" }, { status: 400 });
    }
    transcript = {
      transcript: text,
      languageCode: /[\u0C80-\u0CFF]/u.test(text) ? "kn-IN" : "en-IN",
    };
  }

  const answerResponse = await fetch(agentUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-whatsapp-internal-secret": process.env.WHATSAPP_INTERNAL_SECRET ?? "",
    },
    body: JSON.stringify({
      from,
      transcript: transcript.transcript,
      languageCode: transcript.languageCode,
    }),
    cache: "no-store",
  });
  if (!answerResponse.ok) {
    return NextResponse.json(
      { error: `HRMS agent service returned HTTP ${answerResponse.status}` },
      { status: 502 },
    );
  }

  const answerBody = (await answerResponse.json()) as { answer?: string };
  if (!answerBody.answer?.trim()) {
    return NextResponse.json({ error: "HRMS agent returned no answer" }, { status: 502 });
  }

  const audio = await sarvamTextToSpeech(answerBody.answer.trim(), transcript.languageCode);
  return NextResponse.json({
    transcript: transcript.transcript,
    languageCode: transcript.languageCode,
    answer: answerBody.answer.trim(),
    audioBase64: audio.audio.toString("base64"),
    audioMimeType: audio.mimeType,
  });
}
