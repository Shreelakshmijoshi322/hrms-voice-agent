import { describe, expect, it } from "vitest";

import { extractInboundMessages } from "@/web/lib/whatsapp";

describe("WhatsApp webhook payloads", () => {
  it("extracts text messages", () => {
    const messages = extractInboundMessages({
      entry: [{
        changes: [{
          value: {
            metadata: { phone_number_id: "phone-id" },
            messages: [{
              id: "message-1",
              from: "919999999999",
              type: "text",
              text: { body: "What is my leave balance?" },
            }],
          },
        }],
      }],
    });

    expect(messages).toEqual([{
      id: "message-1",
      from: "919999999999",
      phoneNumberId: "phone-id",
      type: "text",
      text: "What is my leave balance?",
      mediaId: undefined,
      mimeType: undefined,
      timestamp: undefined,
    }]);
  });

  it("extracts audio messages", () => {
    const messages = extractInboundMessages({
      entry: [{
        changes: [{
          value: {
            messages: [{
              id: "message-2",
              from: "919999999999",
              type: "audio",
              audio: { id: "media-1", mime_type: "audio/ogg" },
            }],
          },
        }],
      }],
    });

    expect(messages[0]).toMatchObject({
      id: "message-2",
      type: "audio",
      mediaId: "media-1",
      mimeType: "audio/ogg",
    });
  });
});
