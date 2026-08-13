import "server-only";

import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

import { verifyDemoSession } from "@/web/lib/session-token";

export const DEMO_SESSION_COOKIE = "people_demo_session";

export async function readDemoSession() {
  const token = (await cookies()).get(DEMO_SESSION_COOKIE)?.value;
  return verifyDemoSession(token);
}

export async function readDemoSessionFromRequest(request: NextRequest) {
  return verifyDemoSession(request.cookies.get(DEMO_SESSION_COOKIE)?.value);
}
