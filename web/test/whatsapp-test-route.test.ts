import { describe, expect, it } from "vitest";

import { POST } from "@/app/api/whatsapp/test/route";

describe("local WhatsApp test route", () => {
  it("returns a mock HRMS reply for text", async () => {
    process.env.WHATSAPP_MOCK_MODE = "true";
    const response = await POST(new Request("http://localhost/api/whatsapp/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "text", text: "What is my leave balance?" }),
    }));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      mode: "mock",
      duplicate: false,
    });
  });
});
