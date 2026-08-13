// @vitest-environment node

import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { POST } from "@/app/api/token/route";
import { authenticateDemoUser } from "@/web/lib/demo-users";
import { signDemoSession } from "@/web/lib/session-token";

const originalEnvironment = { ...process.env };
const TEST_SECRET = "test-session-secret-that-is-at-least-32-characters";

afterEach(() => {
  process.env = { ...originalEnvironment };
});

function decodeJwtPayload(token: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
}

async function authenticatedRequest(
  email: "maya@people.demo" | "priya@people.demo",
  password: string,
) {
  const session = authenticateDemoUser(email, password);
  if (!session) throw new Error("Test credential mismatch");
  const cookie = await signDemoSession(session, TEST_SECRET);
  return new NextRequest("http://localhost/api/token", {
    method: "POST",
    headers: { cookie: `people_demo_session=${cookie}` },
    body: JSON.stringify({
      room_name: "attacker-controlled-room",
      participant_identity: "attacker-controlled-identity",
      role: "attacker-controlled-role",
    }),
  });
}

describe("POST /api/token", () => {
  it("derives employee identity and role from the signed demo session", async () => {
    process.env.LIVEKIT_URL = "wss://voice.example.test";
    process.env.LIVEKIT_API_KEY = "demo-key";
    process.env.LIVEKIT_API_SECRET = "a-secret-long-enough-for-signing";
    process.env.VOICE_AGENT_NAME = "people-agent";
    process.env.DEMO_SESSION_SECRET = TEST_SECRET;

    const response = await POST(
      await authenticatedRequest("maya@people.demo", "employee123"),
    );
    const body = await response.json();

    expect(response.status, JSON.stringify(body)).toBe(201);
    const claims = decodeJwtPayload(body.participant_token);
    expect(body.server_url).toBe("wss://voice.example.test");
    expect(claims.sub).toBe("EMP-1042");
    expect(claims.name).toBe("Maya Patel");
    expect(claims.attributes).toMatchObject({
      app: "hrms-demo",
      "hrms.user_id": "EMP-1042",
      "hrms.role": "employee",
    });
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
  });

  it("derives the HR admin identity and role from its signed session", async () => {
    process.env.LIVEKIT_URL = "wss://voice.example.test";
    process.env.LIVEKIT_API_KEY = "demo-key";
    process.env.LIVEKIT_API_SECRET = "a-secret-long-enough-for-signing";
    process.env.DEMO_SESSION_SECRET = TEST_SECRET;

    const response = await POST(
      await authenticatedRequest("priya@people.demo", "hradmin123"),
    );
    const claims = decodeJwtPayload((await response.json()).participant_token);

    expect(claims.sub).toBe("HR-2001");
    expect(claims.attributes).toMatchObject({
      "hrms.user_id": "HR-2001",
      "hrms.role": "hr_admin",
    });
  });

  it("rejects requests without a valid signed session", async () => {
    process.env.LIVEKIT_URL = "wss://voice.example.test";
    process.env.LIVEKIT_API_KEY = "demo-key";
    process.env.LIVEKIT_API_SECRET = "a-secret-long-enough-for-signing";
    process.env.DEMO_SESSION_SECRET = TEST_SECRET;

    const response = await POST(
      new NextRequest("http://localhost/api/token", { method: "POST" }),
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: "Authentication required" });
  });

  it("returns a safe error when server configuration is missing", async () => {
    delete process.env.LIVEKIT_URL;
    delete process.env.LIVEKIT_API_KEY;
    delete process.env.LIVEKIT_API_SECRET;
    process.env.DEMO_SESSION_SECRET = TEST_SECRET;

    const response = await POST(
      await authenticatedRequest("maya@people.demo", "employee123"),
    );

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({ error: "Server configuration error" });
  });
});
