import { jwtVerify, SignJWT, type JWTPayload } from "jose";

import type { DemoSession } from "@/web/lib/demo-users";

const LOCAL_SESSION_SECRET = "people-demo-local-session-secret-2026";
const ISSUER = "people-demo";
const AUDIENCE = "hrms-voice-demo";

export function getSessionSecret(): string {
  const configured = process.env.DEMO_SESSION_SECRET;
  if (configured) {
    if (configured.length < 32) {
      throw new Error("DEMO_SESSION_SECRET must contain at least 32 characters.");
    }
    return configured;
  }
  if (process.env.NODE_ENV === "production") {
    throw new Error("DEMO_SESSION_SECRET is required in production.");
  }
  return LOCAL_SESSION_SECRET;
}

function encodedSecret(secret: string) {
  return new TextEncoder().encode(secret);
}

export async function signDemoSession(
  session: DemoSession,
  secret = getSessionSecret(),
): Promise<string> {
  return new SignJWT(session as unknown as JWTPayload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setIssuer(ISSUER)
    .setAudience(AUDIENCE)
    .setExpirationTime("12h")
    .sign(encodedSecret(secret));
}

export async function verifyDemoSession(
  token: string | undefined,
  secret = getSessionSecret(),
): Promise<DemoSession | null> {
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, encodedSecret(secret), {
      algorithms: ["HS256"],
      issuer: ISSUER,
      audience: AUDIENCE,
    });
    const { userId, role, name, email } = payload;
    if (
      typeof userId !== "string" ||
      (role !== "employee" && role !== "hr_admin") ||
      typeof name !== "string" ||
      typeof email !== "string"
    ) {
      return null;
    }
    return { userId, role, name, email };
  } catch {
    return null;
  }
}
