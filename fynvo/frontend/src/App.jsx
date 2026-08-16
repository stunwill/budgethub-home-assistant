import { useEffect, useMemo, useState } from 'react';

const navigation = ['Overview', 'Cash Flow', 'Recurring Expenses', 'Income', 'Planned Spending', 'Calendar', 'Categories', 'Reports', 'Settings'];
const currencyFormatter = new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' });
const dateFormatter = new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: 'numeric', month: 'short' });

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || 'Something went wrong');
  }
  return response.json();
}

function LogoMark() {
  return <div className="logo-mark" aria-hidden="true">F</div>;
}

function LoginScreen({ setupRequired, onAuthenticated }) {
  const [mode, setMode] = useState(setupRequired ? 'setup' : 'login');
  const [form, setForm] = useState({ username: '', display_name: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => setMode(setupRequired ? 'setup' : 'login'), [setupRequired]);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const path = mode === 'setup' ? '/api/auth/setup' : '/api/auth/login';
      const payload = mode === 'setup'
        ? { username: form.username, display_name: form.display_name || form.username, password: form.password }
        : { username: form.username, password: form.password };
      const user = await api(path, { method: 'POST', body: JSON.stringify(payload) });
      onAuthenticated(user);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <LogoMark />
        <p className="eyebrow">Know what's coming.</p>
        <h1>{mode === 'setup' ? 'Create your Fynvo admin' : 'Sign in to Fynvo'}</h1>
        <p className="muted">Your financial dashboard is protected. Sign in before viewing household finance data.</p>
        <form onSubmit={submit} className="form-stack">
          <label>Username<input autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required /></label>
          {mode === 'setup' && <label>Display name<input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} placeholder="Stu" /></label>}
          <label>Password<input type="password" autoComplete={mode === 'setup' ? 'new-password' : 'current-password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={mode === 'setup' ? 8 : 1} /></label>
          {error && <div className="error-state">{error}</div>}
          <button className="primary-button" disabled={loading}>{loading ? 'Please wait…' : mode === 'setup' ? 'Create admin account' : 'Sign in'}</button>
        </form>
      </section>
    </main>
  );
}

function SummaryCard({ title, value, subtitle }) {
  return <article className="summary-card"><p>{title}</p><strong>{currencyFormatter.format(value || 0)}</strong><span>{subtitle}</span></article>;
}

function EmptyState({ title, children }) {
  return <div className="empty-state"><strong>{title}</strong><p>{children}</p></div>;
}

function Overview({ user, onLogout }) {
  const [rangeDays, setRangeDays] = useState(90);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setError('');
    api(`/api/dashboard/overview?range_days=${rangeDays}`).then(setDashboard).catch((error) => setError(error.message));
  }, [rangeDays]);

  const today = useMemo(() => dateFormatter.format(new Date()), []);
  const summary = dashboard?.summary || { income: 0, recurring_bills: 0, planned_spending: 0, projected_balance: 0 };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row"><LogoMark /><div><strong>Fynvo</strong><span>Know what's coming.</span></div></div>
        <nav>{navigation.map((item, index) => <button className={index === 0 ? 'nav-item active' : 'nav-item'} key={item}>{item}</button>)}</nav>
      </aside>
      <main className="content">
        <header className="page-header">
          <div><p className="eyebrow">{today}</p><h1>Welcome back, {user.display_name}</h1><p className="muted">Your financial overview is ready. Future modules will feed this dashboard with real household finance data.</p></div>
          <div className="header-actions"><select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}><option value="30">Next 30 days</option><option value="60">Next 60 days</option><option value="90">Next 90 days</option></select><button className="secondary-button" onClick={onLogout}>Logout</button></div>
        </header>
        {error && <div className="error-state">{error}</div>}
        <section className="summary-grid"><SummaryCard title="Income" value={summary.income} subtitle={`Next ${rangeDays} days`} /><SummaryCard title="Recurring Bills" value={summary.recurring_bills} subtitle="Expected commitments" /><SummaryCard title="Planned Spending" value={summary.planned_spending} subtitle="Included scenarios" /><SummaryCard title="Projected Balance" value={summary.projected_balance} subtitle="Forecast placeholder" /></section>
        <section className="dashboard-grid">
          <article className="panel wide"><div className="panel-header"><div><p className="eyebrow">Cash Flow Forecast</p><h2>Projected balance framework</h2></div><button className="link-button">Open Cash Flow</button></div><div className="chart-shell"><div className="axis y-axis">Balance</div><div className="chart-empty">Cash-flow chart will appear once accounts, income and expenses exist.</div><div className="axis x-axis">Time</div></div></article>
          <article className="panel"><p className="eyebrow">Upcoming</p><h2>Financial events</h2><EmptyState title="No upcoming events yet">Income, recurring bills and planned spending will appear here in future releases.</EmptyState></article>
          <article className="panel"><p className="eyebrow">Top Planned Spending</p><h2>Planned purchases</h2><EmptyState title="Nothing planned yet">Add planned spending in v0.5.0 to see priority items here.</EmptyState></article>
          <article className="panel wide"><p className="eyebrow">Quick Stats</p><h2>Financial metrics</h2><div className="stats-row"><EmptyState title="Metrics waiting for data">Average monthly income, recurring expenses, planned spending and surplus will calculate from real data.</EmptyState></div></article>
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState({ loading: true, authenticated: false, setup_required: false, user: null });
  useEffect(() => { api('/api/auth/state').then((data) => setState({ loading: false, ...data })).catch(() => setState({ loading: false, authenticated: false, setup_required: true, user: null })); }, []);
  async function logout() { await api('/api/auth/logout', { method: 'POST' }); setState({ loading: false, authenticated: false, setup_required: false, user: null }); }
  if (state.loading) return <main className="loading-screen"><LogoMark /><p>Loading Fynvo…</p></main>;
  if (!state.authenticated) return <LoginScreen setupRequired={state.setup_required} onAuthenticated={(user) => setState({ loading: false, authenticated: true, setup_required: false, user })} />;
  return <Overview user={state.user} onLogout={logout} />;
}
