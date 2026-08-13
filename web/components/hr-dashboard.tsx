import type { ReactNode } from "react";
import {
  Bell,
  CalendarDays,
  ChevronRight,
  CircleUserRound,
  Clock3,
  FileText,
  Gift,
  Grid2X2,
  HandCoins,
  GraduationCap,
  ListChecks,
  LogOut,
  Plane,
  Search,
  Settings,
  UsersRound,
} from "lucide-react";

import type { DemoSession } from "@/web/lib/demo-users";

type HRDashboardProps = {
  assistant: ReactNode;
  onLogout?: () => void;
  session?: DemoSession;
};

const navigation = [
  ["Overview", Grid2X2],
  ["Time off", Plane],
  ["Payroll", HandCoins],
  ["People", UsersRound],
  ["Documents", FileText],
] as const;

export function HRDashboard({ assistant, onLogout, session }: HRDashboardProps) {
  const employeeName = session?.name ?? "Maya Patel";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="People home">
          <span className="brand-symbol">P</span>
          <span>people</span>
        </a>
        <nav aria-label="Main navigation">
          {navigation.map(([label, Icon], index) => (
            <a className={index === 0 ? "nav-item active" : "nav-item"} href="#" key={label}>
              <Icon size={19} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <a className="nav-item settings-link" href="#">
          <Settings size={19} />
          <span>Settings</span>
        </a>
        <div className="profile-chip">
          <div className="avatar avatar-small">MP</div>
          <div><strong>{employeeName}</strong><span>Employee</span></div>
        </div>
      </aside>

      <main className="dashboard">
        <header className="topbar">
          <div className="search-box">
            <Search size={18} />
            <span>Search people, policies, documents…</span>
            <kbd>⌘ K</kbd>
          </div>
          <button className="topbar-icon" type="button" aria-label="Notifications"><Bell size={19} /></button>
          <span className="role-badge">Employee</span>
          <button className="logout-button" onClick={onLogout} type="button"><LogOut size={15} /> Log out</button>
          <div className="avatar avatar-small">MP</div>
        </header>

        <div className="dashboard-body">
          <div className="welcome-row">
            <div>
              <p className="date-label">Thursday, August 13</p>
              <h1>Good morning, Maya</h1>
              <p>Here’s what’s happening with your work life today.</p>
            </div>
            <button className="request-button" type="button"><Plane size={17} /> Request time off</button>
          </div>

          <div className="dashboard-grid">
            <section className="content-column">
              <article className="employee-card">
                <div className="avatar avatar-large">MP</div>
                <div className="employee-copy">
                  <span className="employee-state"><span /> Active</span>
                  <h2>Maya Patel</h2>
                  <p>Product Designer · Product &amp; Design</p>
                  <div className="employee-meta">
                    <span><CircleUserRound size={15} /> Manager: Jordan Lee</span>
                    <span><Clock3 size={15} /> Bengaluru · 10:32 AM</span>
                  </div>
                </div>
                <button className="more-button" aria-label="Open employee profile" type="button"><ChevronRight /></button>
              </article>

              <div className="metrics-grid">
                <article className="metric-card accent-blue">
                  <div className="metric-icon"><Plane size={19} /></div>
                  <span>Vacation balance</span>
                  <strong>12 days</strong>
                  <small>of 24 days remaining</small>
                  <div className="progress"><span style={{ width: "50%" }} /></div>
                </article>
                <article className="metric-card accent-violet">
                  <div className="metric-icon"><HandCoins size={19} /></div>
                  <span>Latest payslip</span>
                  <strong>July 2026</strong>
                  <small>Paid on July 31</small>
                  <a href="#">View payslip <ChevronRight size={14} /></a>
                </article>
                <article className="metric-card accent-orange">
                  <div className="metric-icon"><Gift size={19} /></div>
                  <span>Next holiday</span>
                  <strong>Independence Day</strong>
                  <small>Saturday, August 15</small>
                  <span className="days-away">In 2 days</span>
                </article>
              </div>

              <article className="activity-card">
                <div className="section-heading"><div><p className="eyebrow">This week</p><h2>Upcoming</h2></div><a href="#">View calendar</a></div>
                <div className="event-row">
                  <div className="event-date"><strong>14</strong><span>FRI</span></div>
                  <div className="event-icon blue"><CalendarDays size={17} /></div>
                  <div><strong>Design weekly sync</strong><span>10:00 AM · Product Studio</span></div>
                  <span className="event-duration">45 min</span>
                </div>
                <div className="event-row">
                  <div className="event-date"><strong>15</strong><span>SAT</span></div>
                  <div className="event-icon orange"><Gift size={17} /></div>
                  <div><strong>Independence Day</strong><span>Public holiday · India</span></div>
                  <span className="holiday-label">Holiday</span>
                </div>
              </article>

              <div className="secondary-grid">
                <article className="activity-card compact-card">
                  <div className="section-heading"><div><p className="eyebrow">Focus</p><h2><ListChecks size={17} /> Priority tasks</h2></div></div>
                  <p><strong>Prepare checkout usability review</strong><span>High priority · Due Aug 14</span></p>
                  <p><strong>Update design-system empty states</strong><span>High priority · Due Aug 15</span></p>
                </article>
                <article className="activity-card compact-card">
                  <div className="section-heading"><div><p className="eyebrow">Learning</p><h2><GraduationCap size={17} /> Development</h2></div></div>
                  <p><strong>Creative Facilitation Lab</strong><span>Workshop · Starts Sep 4 · 8 seats</span></p>
                  <p><strong>Advanced Figma Systems</strong><span>Product &amp; Design cohort</span></p>
                </article>
              </div>
            </section>
            <aside className="assistant-column">{assistant}</aside>
          </div>
        </div>
      </main>
    </div>
  );
}
