import { NextResponse } from "next/server";

import { authenticateDemoUser } from "@/web/lib/demo-users";
import { DEMO_SESSION_COOKIE } from "@/web/lib/server-session";
import { signDemoSession } from "@/web/lib/session-token";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid demo credentials" }, { status: 401 });
  }
  const { email, password } = body as { email?: unknown; password?: unknown };
  if (typeof email !== "string" || typeof password !== "string") {
    return NextResponse.json({ error: "Invalid demo credentials" }, { status: 401 });
  }
  const session = authenticateDemoUser(email, password);
  if (!session) {
    return NextResponse.json({ error: "Invalid demo credentials" }, { status: 401 });
  }
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(DEMO_SESSION_COOKIE, await signDemoSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return response;
}
