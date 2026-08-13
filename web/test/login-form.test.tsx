import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/web/components/login-form";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LoginForm", () => {
  it("submits selected demo credentials and redirects after success", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    const assign = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("location", { assign });
    render(<LoginForm />);

    await user.click(screen.getByRole("button", { name: "Continue as employee" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      email: "maya@people.demo",
      password: "employee123",
    });
    expect(assign).toHaveBeenCalledWith("/");
  });

  it("shows a safe invalid-credential error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    render(<LoginForm />);

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Check the demo email and password",
    );
  });
});
