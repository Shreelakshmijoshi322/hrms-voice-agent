import "server-only";

import {
  downloadWhatsAppMedia,
  sendWhatsAppAudio,
  sendWhatsAppText,
  sendWhatsAppTypingIndicator,
  uploadWhatsAppMedia,
} from "@/web/lib/whatsapp-meta";

export type WhatsAppInboundMessage = {
  id: string;
  from: string;
  phoneNumberId: string;
  type: "text" | "audio" | "unknown";
  text?: string;
  mediaId?: string;
  mimeType?: string;
  timestamp?: string;
};

export type WhatsAppProcessingResult = {
  duplicate: boolean;
  replyText?: string;
  mode: "mock" | "live";
};

type ProcessorResponse = {
  replyText?: string;
  audioBase64?: string;
  audioMimeType?: string;
};

type MetaWebhookPayload = {
  entry?: Array<{
    changes?: Array<{
      value?: {
        metadata?: { phone_number_id?: string };
        messages?: Array<{
          from?: string;
          id?: string;
          timestamp?: string;
          type?: string;
          text?: { body?: string };
          audio?: { id?: string; mime_type?: string };
        }>;
      };
    }>;
  }>;
};

// This is deliberately process-local for the development MVP. Production
// should move this check into the database/queue using message IDs as a
// unique key, because serverless instances do not share memory.
const seenMessageIds = new Set<string>();
const processingMessageIds = new Set<string>();

export function extractInboundMessages(payload: MetaWebhookPayload): WhatsAppInboundMessage[] {
  const messages: WhatsAppInboundMessage[] = [];

  for (const entry of payload.entry ?? []) {
    for (const change of entry.changes ?? []) {
      const value = change.value;
      const phoneNumberId = value?.metadata?.phone_number_id ?? "";

      for (const message of value?.messages ?? []) {
        if (!message.id || !message.from) continue;

        const type = message.type === "text"
          ? "text"
          : message.type === "audio"
            ? "audio"
            : "unknown";

        messages.push({
          id: message.id,
          from: message.from,
          phoneNumberId,
          type,
          text: message.text?.body,
          mediaId: message.audio?.id,
          mimeType: message.audio?.mime_type,
          timestamp: message.timestamp,
        });
      }
    }
  }

  return messages;
}

function redactPhone(phone: string): string {
  return phone.length > 4 ? `${"*".repeat(phone.length - 4)}${phone.slice(-4)}` : "****";
}

/**
 * Development processing boundary. This intentionally does not call Meta or
 * AI providers until credentials and employee authentication are configured.
 * It gives us a safe webhook to test while the Meta account is under review.
 */
export async function processInboundMessage(
  message: WhatsAppInboundMessage,
): Promise<WhatsAppProcessingResult> {
  if (seenMessageIds.has(message.id) || processingMessageIds.has(message.id)) {
    return { duplicate: true, mode: "mock" };
  }
  processingMessageIds.add(message.id);

  const mockMode = (process.env.WHATSAPP_MOCK_MODE ?? "true").toLowerCase() !== "false";
  if (mockMode) {
    const replyText = message.type === "audio"
      ? "Demo mode: I received your voice message. Meta and Sarvam audio processing will be connected after Meta approval."
      : message.text?.toLowerCase().includes("leave") || message.text?.includes("ರಜೆ")
        ? "Demo mode: your leave request was received. Live HRMS lookup will be connected after WhatsApp authentication is enabled."
        : "Demo mode: your WhatsApp message was received by the HRMS assistant.";

    console.info("WhatsApp mock message received", {
      id: message.id,
      from: redactPhone(message.from),
      type: message.type,
      hasText: Boolean(message.text),
      hasMedia: Boolean(message.mediaId),
    });
    seenMessageIds.add(message.id);
    processingMessageIds.delete(message.id);
    return { duplicate: false, replyText, mode: "mock" };
  }

  const processorUrl = process.env.WHATSAPP_AUDIO_PROCESSOR_URL?.trim();
  if (!processorUrl) {
    processingMessageIds.delete(message.id);
    throw new Error(
      "Live WhatsApp processing needs WHATSAPP_AUDIO_PROCESSOR_URL. The Meta media client is ready, but the Sarvam/STT/HRMS/TTS worker is not exposed as an HTTP service yet.",
    );
  }

  let typingRefresh: ReturnType<typeof setInterval> | undefined;
  try {
    // WhatsApp typing indicators are temporary. Refresh periodically because
    // audio/STT, HRMS lookup, LLM, and TTS can take longer than one indicator
    // window. A failure here must not prevent the actual answer.
    try {
      await sendWhatsAppTypingIndicator(message.id);
      typingRefresh = setInterval(() => {
        void sendWhatsAppTypingIndicator(message.id).catch((error: unknown) => {
          console.warn("WhatsApp typing indicator refresh failed", error);
        });
      }, 15_000);
    } catch (error) {
      console.warn("WhatsApp typing indicator could not be shown", error);
    }

    let response: Response;
    if (message.type === "audio") {
      if (!message.mediaId) throw new Error("WhatsApp audio message has no media ID.");
      const media = await downloadWhatsAppMedia(message.mediaId);
      const form = new FormData();
      form.append("message_id", message.id);
      form.append("from", message.from);
      form.append("mime_type", media.mimeType);
      form.append(
        "file",
        new Blob([new Uint8Array(media.bytes).buffer as ArrayBuffer], { type: media.mimeType }),
        "input-audio",
      );
      response = await fetch(processorUrl, {
        method: "POST",
        headers: { "x-whatsapp-internal-secret": process.env.WHATSAPP_INTERNAL_SECRET ?? "" },
        body: form,
        cache: "no-store",
      });
    } else {
      response = await fetch(processorUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-whatsapp-internal-secret": process.env.WHATSAPP_INTERNAL_SECRET ?? "",
        },
        body: JSON.stringify({
          message_id: message.id,
          from: message.from,
          text: message.text ?? "",
        }),
        cache: "no-store",
      });
    }

    if (!response.ok) throw new Error(`WhatsApp audio processor returned HTTP ${response.status}.`);
    const result = (await response.json()) as ProcessorResponse;
    if (result.audioBase64) {
      const media = await uploadWhatsAppMedia(
        Buffer.from(result.audioBase64, "base64"),
        result.audioMimeType || "audio/ogg; codecs=opus",
      );
      await sendWhatsAppAudio(message.from, media.id);
    } else if (result.replyText?.trim()) {
      await sendWhatsAppText(message.from, result.replyText.trim());
    } else {
      throw new Error("WhatsApp audio processor returned neither audioBase64 nor replyText.");
    }

    seenMessageIds.add(message.id);
    return { duplicate: false, mode: "live" };
  } finally {
    if (typingRefresh) clearInterval(typingRefresh);
    processingMessageIds.delete(message.id);
  }
}
