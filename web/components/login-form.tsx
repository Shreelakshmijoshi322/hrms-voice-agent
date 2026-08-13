"use client";

import { FormEvent, useState } from "react";
import { BriefcaseBusiness, ShieldCheck } from "lucide-react";

const accounts = {
  employee: { email: "maya@people.demo", password: "employee123" },
  hr_admin: { email: "priya@people.demo", password: "hradmin123" },
} as const;

export function LoginForm() {
  const [email, setEmail] = useState<string>(accounts.employee.email);
  const [password, setPassword] = useState<string>(accounts.employee.password);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitCredentials(credentials: { email: string; password: string }) {
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(credentials),
      });
      if (!response.ok) {
        setError("Check the demo email and password, then try again.");
        return;
      }
      globalThis.location.assign("/");
    } catch {
      setError("The demo sign-in service is unavailable. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function chooseAccount(role: keyof typeof accounts) {
    const account = accounts[role];
    setEmail(account.email);
    setPassword(account.password);
    void submitCredentials(account);
  }

  function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitCredentials({ email, password });
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand"><span className="brand-symbol">P</span><span>people</span></div>
        <p className="demo-kicker"><ShieldCheck size={14} /> Fictional HRMS demo</p>
        <h1 id="login-title">Choose your workspace</h1>
        <p className="login-intro">Try the same voice assistant with employee and HR permissions.</p>

        <div className="account-grid">
          <article className="account-card">
            <span className="account-icon"><BriefcaseBusiness size={20} /></span>
            <div><strong>Maya Patel</strong><span>Employee · Product Designer</span></div>
            <button disabled={submitting} onClick={() => chooseAccount("employee")} type="button">Continue as employee</button>
          </article>
          <article className="account-card account-card-hr">
            <span className="account-icon"><ShieldCheck size={20} /></span>
            <div><strong>Priya Sharma</strong><span>HR Admin · Operations Manager</span></div>
            <button disabled={submitting} onClick={() => chooseAccount("hr_admin")} type="button">Continue as HR Admin</button>
          </article>
        </div>

        <div className="login-divider"><span>or enter a demo account</span></div>
        <form className="login-form" onSubmit={submitLogin}>
          <label>Email<input autoComplete="username" name="email" onChange={(event) => setEmail(event.target.value)} type="email" value={email} /></label>
          <label>Password<input autoComplete="current-password" name="password" onChange={(event) => setPassword(event.target.value)} type="password" value={password} /></label>
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button disabled={submitting} type="submit">{submitting ? "Signing in…" : "Sign in"}</button>
        </form>
        <p className="login-note">All people, records, actions, and credentials on this screen are demo-only.</p>
      </section>
    </main>
  );
}
