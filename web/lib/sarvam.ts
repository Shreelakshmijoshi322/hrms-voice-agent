import "server-only";

const SARVAM_API = "https://api.sarvam.ai";

function apiKey(): string {
  const value = process.env.SARVAM_API_KEY?.trim();
  if (!value) throw new Error("Missing SARVAM_API_KEY in .env.local.");
  return value;
}

export type SarvamTranscript = {
  transcript: string;
  languageCode: string;
};

export async function sarvamSpeechToText(file: File): Promise<SarvamTranscript> {
  const form = new FormData();
  form.append("file", file, file.name || "whatsapp-audio");
  form.append("model", process.env.SARVAM_STT_MODEL?.trim() || "saaras:v4");
  form.append("mode", process.env.SARVAM_STT_MODE?.trim() || "codemix");

  const response = await fetch(`${SARVAM_API}/speech-to-text`, {
    method: "POST",
    headers: { "api-subscription-key": apiKey() },
    body: form,
    cache: "no-store",
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`Sarvam STT ${response.status}: ${body}`);
  const parsed = JSON.parse(body) as { transcript?: string; language_code?: string };
  if (!parsed.transcript?.trim()) throw new Error("Sarvam STT returned an empty transcript.");
  return {
    transcript: parsed.transcript.trim(),
    languageCode: parsed.language_code || "en-IN",
  };
}

export async function sarvamTextToSpeech(
  text: string,
  languageCode: string,
): Promise<{ audio: Buffer; mimeType: string }> {
  const response = await fetch(`${SARVAM_API}/text-to-speech`, {
    method: "POST",
    headers: {
      "api-subscription-key": apiKey(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      model: process.env.SARVAM_TTS_MODEL?.trim() || "bulbul:v3",
      speaker: process.env.SARVAM_TTS_SPEAKER?.trim() || "shubh",
      language_code: languageCode.startsWith("kn") ? "kn-IN" : "en-IN",
      output_audio_codec: "opus",
      speech_sample_rate: 24000,
    }),
    cache: "no-store",
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`Sarvam TTS ${response.status}: ${body}`);
  const parsed = JSON.parse(body) as { audios?: string[] };
  const encoded = parsed.audios?.[0];
  if (!encoded) throw new Error("Sarvam TTS returned no audio.");
  return { audio: Buffer.from(encoded, "base64"), mimeType: "audio/ogg" };
}
