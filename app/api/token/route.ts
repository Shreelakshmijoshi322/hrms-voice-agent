import {
  AccessToken,
  RoomAgentDispatch,
  RoomConfiguration,
  TrackSource,
} from "livekit-server-sdk";
import { createCipheriv, createHash, randomBytes } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { readDemoSessionFromRequest } from "@/web/lib/server-session";

type VoiceIdentity = {
  userId: string;
  tenantId: string;
  role: "employee" | "hr_admin";
  name: string;
  sessionCookie?: string;
};

function roleFromHRMSRoles(roles: unknown): "employee" | "hr_admin" {
  const values = Array.isArray(roles) ? roles.map((role) => String(role).toLowerCase()) : [];
  return values.some((role) => role.includes("admin") || role.includes("hr"))
    ? "hr_admin"
    : "employee";
}

function displayName(email: string | undefined): string {
  const local = (email ?? "").split("@")[0] ?? "HRMS user";
  const first = local.split(/[._-]/)[0] ?? "HRMS user";
  return first ? first.charAt(0).toUpperCase() + first.slice(1) : "HRMS user";
}

async function readHRMSIdentity(request: NextRequest): Promise<VoiceIdentity | null> {
  const cookie = request.headers.get("cookie");
  if (!cookie) return null;

  const coreURL = process.env.HRMS_CORE_URL ?? "http://localhost:8081";
  try {
    const response = await fetch(`${coreURL.replace(/\/$/, "")}/auth/session`, {
      headers: { cookie },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { data?: { user?: Record<string, unknown> } };
    const user = body.data?.user;
    if (!user?.id || !user.tenant_id) return null;
    const email = typeof user.email === "string" ? user.email : undefined;
    return {
      userId: String(user.id),
      tenantId: String(user.tenant_id),
      role: roleFromHRMSRoles(user.roles),
      name: displayName(email),
      sessionCookie: cookie,
    };
  } catch {
    return null;
  }
}

function encryptSessionCookie(cookie: string, apiSecret: string): string {
  // The encrypted value is visible as participant metadata, but only the
  // server-side voice agent has the derived key needed to decrypt it.
  const key = createHash("sha256").update(`${apiSecret}:hrms-session-cookie`).digest();
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const ciphertext = Buffer.concat([cipher.update(cookie, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ["v1", iv, tag, ciphertext]
    .map((part) => (typeof part === "string" ? part : part.toString("base64url")))
    .join(".");
}

function corsHeaders(request: NextRequest): HeadersInit {
  const origin = request.headers.get("origin");
  const allowed = process.env.VOICE_UI_ORIGIN ?? "http://localhost:3000";
  return origin === allowed
    ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true" }
    : {};
}

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, {
    status: 204,
    headers: {
      ...corsHeaders(request),
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

export async function POST(request: NextRequest) {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const serverUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !serverUrl) {
    return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
  }

  try {
    const hrmsIdentity = await readHRMSIdentity(request);
    const demoSession = hrmsIdentity ? null : await readDemoSessionFromRequest(request);
    if (!hrmsIdentity && !demoSession) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const roomName = `hr-demo-${crypto.randomUUID()}`;
    const agentName = process.env.VOICE_AGENT_NAME || "hr-assistant";
    const identity: VoiceIdentity = hrmsIdentity ?? {
      userId: demoSession!.userId,
      tenantId: "demo",
      role: demoSession!.role,
      name: demoSession!.name,
    };

    const attributes: Record<string, string> = {
      app: "hrms-demo",
      "hrms.user_id": identity.userId,
      "hrms.tenant_id": identity.tenantId,
      "hrms.role": identity.role,
      "hrms.name": identity.name,
    };
    if (identity.sessionCookie) {
      attributes["hrms.session_cookie"] = encryptSessionCookie(identity.sessionCookie, apiSecret);
    }

    const token = new AccessToken(apiKey, apiSecret, {
      identity: identity.userId,
      name: identity.name,
      attributes,
      ttl: "10m",
    });
    token.addGrant({
      roomJoin: true,
      room: roomName,
      canPublishSources: [TrackSource.MICROPHONE],
      canPublishData: false,
      canSubscribe: true,
    });
    token.roomConfig = new RoomConfiguration({
      agents: [new RoomAgentDispatch({ agentName })],
    });

    return NextResponse.json(
      { server_url: serverUrl, participant_token: await token.toJwt() },
      { status: 201, headers: corsHeaders(request) },
    );
  } catch {
    return NextResponse.json(
      { error: "Failed to generate token" },
      { status: 500, headers: corsHeaders(request) },
    );
  }
}
