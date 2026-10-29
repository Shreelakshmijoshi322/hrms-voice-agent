import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import {
  extractInboundMessages,
  processInboundMessage,
} from "@/web/lib/whatsapp";

export const runtime = "nodejs";

function sameSecret(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

function verifyMetaSignature(rawBody: string, signature: string | null): boolean {
  const appSecret = process.env.WHATSAPP_APP_SECRET;
  if (!appSecret) return process.env.NODE_ENV !== "production";
  if (!signature?.startsWith("sha256=")) return false;

  const expected = createHmac("sha256", appSecret).update(rawBody).digest("hex");
  return sameSecret(signature.slice("sha256=".length), expected);
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const mode = params.get("hub.mode");
  const token = params.get("hub.verify_token");
  const challenge = params.get("hub.challenge");
  const verifyToken = process.env.WHATSAPP_VERIFY_TOKEN;

  if (mode === "subscribe" && verifyToken && token === verifyToken && challenge) {
    return new Response(challenge, { status: 200 });
  }

  return NextResponse.json({ error: "Webhook verification failed" }, { status: 403 });
}

export async function POST(request: NextRequest) {
  const rawBody = await request.text();
  if (!verifyMetaSignature(rawBody, request.headers.get("x-hub-signature-256"))) {
    return NextResponse.json({ error: "Invalid webhook signature" }, { status: 401 });
  }

  let payload: unknown;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const messages = extractInboundMessages(payload as Parameters<typeof extractInboundMessages>[0]);

  // Acknowledge Meta quickly. A production deployment should hand these to a
  // durable queue; the local MVP uses a fire-and-forget processing boundary.
  for (const message of messages) {
    void processInboundMessage(message).catch((error: unknown) => {
      const detail = error instanceof Error ? error.stack || error.message : String(error);
      console.error(`WhatsApp message processing failed (${message.id}): ${detail}`);
    });
  }

  return NextResponse.json({ received: true, messageCount: messages.length });
}
