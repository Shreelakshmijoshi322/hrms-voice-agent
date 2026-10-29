import "server-only";

const DEFAULT_GRAPH_VERSION = "v23.0";

function configValue(name: string): string {
  return process.env[name]?.trim() ?? "";
}

function requireConfig(name: string): string {
  const value = configValue(name);
  if (!value) throw new Error(`Missing ${name} in .env.local.`);
  return value;
}

function graphUrl(path: string): string {
  const version = configValue("WHATSAPP_GRAPH_API_VERSION") || DEFAULT_GRAPH_VERSION;
  return `https://graph.facebook.com/${version}/${path.replace(/^\//, "")}`;
}

async function graphRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = requireConfig("WHATSAPP_ACCESS_TOKEN");
  const response = await fetch(graphUrl(path), {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  const body = await response.text();
  let parsed: unknown = body;
  try {
    parsed = body ? JSON.parse(body) : null;
  } catch {
    // Binary media responses are handled by downloadWhatsAppMedia instead.
  }

  if (!response.ok) {
    const detail = typeof parsed === "string" ? parsed : JSON.stringify(parsed);
    throw new Error(`Meta Graph API ${response.status}: ${detail}`);
  }
  return parsed as T;
}

export type WhatsAppMedia = {
  id: string;
  url: string;
  mime_type?: string;
  sha256?: string;
  file_size?: number;
};

export async function getWhatsAppMedia(mediaId: string): Promise<WhatsAppMedia> {
  return graphRequest<WhatsAppMedia>(mediaId);
}

export async function downloadWhatsAppMedia(mediaId: string): Promise<{
  bytes: Buffer;
  mimeType: string;
}> {
  const media = await getWhatsAppMedia(mediaId);
  const token = requireConfig("WHATSAPP_ACCESS_TOKEN");
  const response = await fetch(media.url, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Meta media download failed with HTTP ${response.status}.`);
  }
  return {
    bytes: Buffer.from(await response.arrayBuffer()),
    mimeType: media.mime_type || "audio/ogg",
  };
}

export async function uploadWhatsAppMedia(
  bytes: Buffer,
  mimeType = "audio/ogg; codecs=opus",
): Promise<{ id: string }> {
  const phoneNumberId = requireConfig("WHATSAPP_PHONE_NUMBER_ID");
  const token = requireConfig("WHATSAPP_ACCESS_TOKEN");
  const form = new FormData();
  form.append("messaging_product", "whatsapp");
  form.append("type", mimeType.split(";")[0]);
  form.append(
    "file",
    new Blob([new Uint8Array(bytes).buffer as ArrayBuffer], { type: mimeType }),
    "reply.ogg",
  );

  return graphRequest<{ id: string }>(`${phoneNumberId}/media`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
}

export async function sendWhatsAppText(to: string, body: string): Promise<void> {
  const phoneNumberId = requireConfig("WHATSAPP_PHONE_NUMBER_ID");
  await graphRequest(`${phoneNumberId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "text",
      text: { preview_url: false, body },
    }),
  });
}

export async function sendWhatsAppAudio(to: string, mediaId: string): Promise<void> {
  const phoneNumberId = requireConfig("WHATSAPP_PHONE_NUMBER_ID");
  await graphRequest(`${phoneNumberId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "audio",
      audio: { id: mediaId },
    }),
  });
}

/**
 * Show WhatsApp's temporary typing indicator while an inbound message is
 * being processed. Meta clears it when we send the actual reply.
 */
export async function sendWhatsAppTypingIndicator(messageId: string): Promise<void> {
  const phoneNumberId = requireConfig("WHATSAPP_PHONE_NUMBER_ID");
  await graphRequest(`${phoneNumberId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      status: "read",
      message_id: messageId,
      typing_indicator: { type: "text" },
    }),
  });
}
