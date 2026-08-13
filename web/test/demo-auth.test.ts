// @vitest-environment node

import { afterEach, describe, expect, it } from "vitest";

import { POST as login } from "@/app/api/auth/login/route";
import { POST as logout } from "@/app/api/auth/logout/route";
import { authenticateDemoUser } from "@/web/lib/demo-users";
import { signDemoSession, verifyDemoSession } from "@/web/lib/session-token";

const TEST_SECRET = "test-session-secret-that-is-at-least-32-characters";
const originalEnvironment = { ...process.env };

afterEach(() => {
  process.env = { ...originalEnvironment };
});

describe("demo authentication", () => {
  it("authenticates only the two exact demo accounts", () => {
    expect(authenticateDemoUser("maya@people.demo", "employee123")).toMatchObject({
      userId: "EMP-1042",
      role: "employee",
    });
    expect(authenticateDemoUser("priya@people.demo", "hradmin123")).toMatchObject({
      userId: "HR-2001",
      role: "hr_admin",
    });
    expect(authenticateDemoUser("maya@people.demo", "wrong")).toBeNull();
  });

  it("rejects a modified signed session", async () => {
    const employeeSession = authenticateDemoUser("maya@people.demo", "employee123");
    expect(employeeSession).not.toBeNull();

    const token = await signDemoSession(employeeSession!, TEST_SECRET);

    await expect(verifyDemoSession(`${token}x`, TEST_SECRET)).resolves.toBeNull();
  });

  it("sets and clears an http-only demo session cookie", async () => {
    process.env.DEMO_SESSION_SECRET = TEST_SECRET;
    const response = await login(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: "priya@people.demo",
          password: "hradmin123",
        }),
      }),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toContain("people_demo_session=");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(response.headers.get("set-cookie")).toContain("SameSite=lax");

    const logoutResponse = await logout();
    expect(logoutResponse.status).toBe(204);
    expect(logoutResponse.headers.get("set-cookie")).toContain("Max-Age=0");
  });

  it("rejects invalid credentials without setting a cookie", async () => {
    const response = await login(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: "maya@people.demo", password: "wrong" }),
      }),
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: "Invalid demo credentials" });
    expect(response.headers.get("set-cookie")).toBeNull();
  });
});
