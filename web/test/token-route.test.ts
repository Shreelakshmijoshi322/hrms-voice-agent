// @vitest-environment node

import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { POST } from "@/app/api/token/route";

const originalEnvironment = { ...process.env };

afterEach(() => {
  process.env = { ...originalEnvironment };
});

function decodeJwtPayload(token: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
}

describe("POST /api/token", () => {
  it("returns a locked-down token that dispatches the configured HR agent", () => {
    process.env.LIVEKIT_URL = "wss://voice.example.test";
    process.env.LIVEKIT_API_KEY = "demo-key";
    process.env.LIVEKIT_API_SECRET = "a-secret-long-enough-for-signing";
    process.env.VOICE_AGENT_NAME = "people-agent";

    const request = new NextRequest("http://localhost/api/token", {
      method: "POST",
      body: JSON.stringify({
        room_name: "attacker-controlled-room",
        participant_identity: "attacker-controlled-identity",
        participant_name: "Attacker",
        room_config: { agents: [{ agent_name: "untrusted-agent" }] },
      }),
    });

    return POST(request).then(async (response) => {
      const body = await response.json();

      expect(response.status, JSON.stringify(body)).toBe(201);
      const claims = decodeJwtPayload(body.participant_token);
      expect(body.server_url).toBe("wss://voice.example.test");
      expect(claims.sub).toBe("EMP-1042");
      expect(claims.name).toBe("Maya Patel");
      expect(claims.video).toMatchObject({
        roomJoin: true,
        canPublishSources: ["microphone"],
        canPublishData: false,
        canSubscribe: true,
      });
      expect((claims.video as { room: string }).room).toMatch(/^hr-demo-/);
      expect((claims.video as { room: string }).room).not.toBe("attacker-controlled-room");
      expect(claims.roomConfig).toMatchObject({
        agents: [{ agentName: "people-agent" }],
      });
      expect(body).not.toHaveProperty("api_secret");
    });
  });

  it("returns a safe error when server configuration is missing", () => {
    delete process.env.LIVEKIT_URL;
    delete process.env.LIVEKIT_API_KEY;
    delete process.env.LIVEKIT_API_SECRET;

    const request = new NextRequest("http://localhost/api/token", {
      method: "POST",
      body: "{}",
    });

    return POST(request).then(async (response) => {
      expect(response.status).toBe(500);
      expect(await response.json()).toEqual({ error: "Server configuration error" });
    });
  });
});
