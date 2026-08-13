import { NextResponse } from "next/server";

import { DEMO_SESSION_COOKIE } from "@/web/lib/server-session";

export async function POST() {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(DEMO_SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return response;
}
