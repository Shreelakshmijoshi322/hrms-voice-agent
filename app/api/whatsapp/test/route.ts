import { NextResponse } from "next/server";

import {
  processInboundMessage,
  type WhatsAppInboundMessage,
} from "@/web/lib/whatsapp";

export const runtime = "nodejs";

export async function POST(request: Request) {
  if ((process.env.WHATSAPP_MOCK_MODE ?? "true").toLowerCase() === "false") {
    return NextResponse.json(
      { error: "The local test endpoint is disabled when WHATSAPP_MOCK_MODE=false." },
      { status: 404 },
    );
  }

  let body: Partial<WhatsAppInboundMessage>;
  try {
    body = (await request.json()) as Partial<WhatsAppInboundMessage>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!body.text?.trim() && body.type !== "audio") {
    return NextResponse.json({ error: "Enter a text message or choose voice message." }, { status: 400 });
  }

  const message: WhatsAppInboundMessage = {
    id: `local-test-${crypto.randomUUID()}`,
    from: body.from?.trim() || "local-test-user",
    phoneNumberId: "local-test-phone",
    type: body.type === "audio" ? "audio" : "text",
    text: body.text?.trim() || undefined,
    mediaId: body.type === "audio" ? "local-test-audio" : undefined,
    mimeType: body.type === "audio" ? "audio/ogg" : undefined,
  };

  const result = await processInboundMessage(message);
  return NextResponse.json({ message, ...result });
}
