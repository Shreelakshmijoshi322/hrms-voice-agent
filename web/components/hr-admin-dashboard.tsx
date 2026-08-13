import type { ReactNode } from "react";
import { Bell, ChevronRight, CircleUserRound, FileCheck2, Grid2X2, LogOut, Search, Settings, ShieldCheck, UsersRound } from "lucide-react";

import type { DemoSession } from "@/web/lib/demo-users";

type Props = { assistant: ReactNode; onLogout?: () => void; session: DemoSession };

const people = [
  ["MP", "Maya Patel", "Product Designer", "Bengaluru"],
  ["JL", "Jordan Lee", "Director of Product Design", "Bengaluru"],
  ["RI", "Rohan Iyer", "Senior Engineer", "Bengaluru"],
] as const;

export function HRAdminDashboard({ assistant, onLogout, session }: Props) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="People home"><span className="brand-symbol">P</span><span>people</span></a>
        <nav aria-label="Main navigation">
          <a className="nav-item active" href="#"><Grid2X2 size={19} /><span>Workforce</span></a>
          <a className="nav-item" href="#"><UsersRound size={19} /><span>Directory</span></a>
          <a className="nav-item" href="#"><FileCheck2 size={19} /><span>Approvals</span></a>
        </nav>
        <a className="nav-item settings-link" href="#"><Settings size={19} /><span>Settings</span></a>
        <div className="profile-chip"><div className="avatar avatar-small avatar-hr">PS</div><div><strong>{session.name}</strong><span>HR Admin</span></div></div>
      </aside>
      <main className="dashboard">
        <header className="topbar">
          <div className="search-box"><Search size={18} /><span>Search employee directory…</span><kbd>⌘ K</kbd></div>
          <span className="role-badge"><ShieldCheck size={14} /> HR Admin</span>
          <button className="topbar-icon" type="button" aria-label="Notifications"><Bell size={19} /></button>
          <button className="logout-button" onClick={onLogout} type="button"><LogOut size={15} /> Log out</button>
        </header>
        <div className="dashboard-body">
          <div className="welcome-row"><div><p className="date-label">Thursday, August 13</p><h1>Good morning, Priya</h1><p>Your fictional People Operations workspace is ready.</p></div></div>
          <div className="dashboard-grid">
            <section className="content-column">
              <div className="metrics-grid admin-metrics">
                <article className="metric-card accent-blue"><div className="metric-icon"><UsersRound size={19} /></div><span>Total employees</span><strong>248</strong><small>Across 5 departments</small></article>
                <article className="metric-card accent-violet"><div className="metric-icon"><CircleUserRound size={19} /></div><span>Out today</span><strong>3</strong><small>2 vacation · 1 sick</small></article>
                <article className="metric-card accent-orange"><div className="metric-icon"><FileCheck2 size={19} /></div><span>Pending approvals</span><strong>1</strong><small>Voice actions require confirmation</small></article>
              </div>
              <article className="activity-card approvals-card">
                <div className="section-heading"><div><p className="eyebrow">Action queue</p><h2>Leave approvals</h2></div><span className="queue-count">1 pending</span></div>
                <div className="approval-row"><div className="avatar avatar-small">MP</div><div><strong>Maya Patel</strong><span>Vacation · Aug 14–20 · 7 days</span></div><span className="pending-label">Pending HR</span></div>
              </article>
              <article className="activity-card directory-card">
                <div className="section-heading"><div><p className="eyebrow">People</p><h2>Employee directory</h2></div><a href="#">View all</a></div>
                {people.map(([initials, name, title, location]) => <div className="directory-row" key={name}><div className="avatar avatar-small">{initials}</div><div><strong>{name}</strong><span>{title} · {location}</span></div><ChevronRight size={16} /></div>)}
              </article>
            </section>
            <aside className="assistant-column">{assistant}</aside>
          </div>
        </div>
      </main>
    </div>
  );
}
