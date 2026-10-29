import { AccessToken, RoomAgentDispatch, RoomConfiguration, TrackSource } from "livekit-server-sdk";
import { createCipheriv, createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type CoreUser = { id?: unknown; email?: unknown; tenant_id?: unknown; roles?: unknown };

function corsHeaders(): HeadersInit {
  return { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" };
}

function roleFromRoles(roles: unknown): "employee" | "hr_admin" {
  const values = Array.isArray(roles) ? roles.map((role) => String(role).toLowerCase()) : [];
  return values.some((role) => role.includes("admin") || role.includes("hr")) ? "hr_admin" : "employee";
}

function displayName(user: CoreUser): string {
  const email = typeof user.email === "string" ? user.email : "HRMS user";
  const first = (email.split("@")[0] ?? "HRMS user").split(/[._-]/)[0] ?? "HRMS user";
  return first ? first.charAt(0).toUpperCase() + first.slice(1) : "HRMS user";
}

function encryptSessionCookie(cookie: string, apiSecret: string): string {
  const key = createHash("sha256").update(`${apiSecret}:hrms-session-cookie`).digest();
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const ciphertext = Buffer.concat([cipher.update(cookie, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ["v1", iv, tag, ciphertext].map((part) => (typeof part === "string" ? part : part.toString("base64url"))).join(".");
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders() });
}

export async function POST(request: Request) {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const serverUrl = process.env.LIVEKIT_URL;
  const coreURL = (process.env.HRMS_CORE_URL ?? "http://localhost:8081").replace(/\/$/, "");
  const mobileSecret = process.env.HRMS_MOBILE_HANDOFF_SECRET ?? process.env.CORE_SESSION_TOKEN_SECRET;
  if (!apiKey || !apiSecret || !serverUrl || !mobileSecret) {
    return NextResponse.json({ error: "Server configuration error" }, { status: 500, headers: corsHeaders() });
  }
  try {
    const body = (await request.json()) as { code?: unknown };
    const code = typeof body.code === "string" ? body.code.trim() : "";
    if (!code) return NextResponse.json({ error: "Mobile sign-in code is required" }, { status: 400, headers: corsHeaders() });
    const response = await fetch(`${coreURL}/auth/mobile/redeem`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-HRMS-Mobile-Secret": mobileSecret },
      body: JSON.stringify({ code }), cache: "no-store",
    });
    const envelope = (await response.json()) as { data?: { session_cookie?: unknown; user?: CoreUser }; error?: { message?: string } };
    const data = envelope.data;
    const user = data?.user;
    const sessionCookie = typeof data?.session_cookie === "string" ? data.session_cookie : "";
    if (!response.ok || !user?.id || !user.tenant_id || !sessionCookie) {
      return NextResponse.json({ error: envelope.error?.message ?? "HRMS sign-in could not be completed" }, { status: response.status === 401 ? 401 : 502, headers: corsHeaders() });
    }
    const identity = { userId: String(user.id), tenantId: String(user.tenant_id), role: roleFromRoles(user.roles), name: displayName(user) };
    const token = new AccessToken(apiKey, apiSecret, {
      identity: identity.userId, name: identity.name,
      attributes: { app: "hrms-mobile", "hrms.user_id": identity.userId, "hrms.tenant_id": identity.tenantId, "hrms.role": identity.role, "hrms.name": identity.name, "hrms.session_cookie": encryptSessionCookie(sessionCookie, apiSecret) },
      ttl: "10m",
    });
    const roomName = `mobile-hrms-${crypto.randomUUID()}`;
    token.addGrant({ roomJoin: true, room: roomName, canPublishSources: [TrackSource.MICROPHONE], canPublishData: false, canSubscribe: true });
    token.roomConfig = new RoomConfiguration({ agents: [new RoomAgentDispatch({ agentName: process.env.VOICE_AGENT_NAME || "hr-assistant" })] });
    return NextResponse.json({ server_url: serverUrl, participant_token: await token.toJwt(), display_name: identity.name }, { status: 201, headers: corsHeaders() });
  } catch {
    return NextResponse.json({ error: "HRMS sign-in service is unavailable" }, { status: 502, headers: corsHeaders() });
  }
}
