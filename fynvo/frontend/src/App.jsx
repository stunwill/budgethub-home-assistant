import { useEffect, useMemo, useState } from 'react';
import logo from './assets/fynvo-logo.svg';
import mark from './assets/fynvo-mark.svg';
import './styles.css';

const api = (path, options = {}) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
const today = new Date().toISOString().slice(0, 10);
const ranges = [
  ['7d', 'Next 7 days'], ['30d', 'Next 30 days'], ['90d', 'Next 90 days'], ['6m', 'Next 6 months'], ['year_end', 'End of year'], ['12m', 'Next 12 months'],
];
const coreNav = ['Overview', 'Cash Flow', 'Calendar', 'Accounts', 'Transactions', 'Recurring Expenses', 'Income', 'Bills', 'Planned Spending'];
const analysisNav = ['Budgeting', 'Reports', 'Insights', 'Scenarios'];
const settingsNav = ['Categories', 'Settings'];
const futurePages = { Budgeting: 'Fully available in v0.8.0. This release prepares the visual and navigation foundation.', Reports: 'Reporting is planned for later releases.', Insights: 'Explainable financial insights are planned for v0.14.0.', Scenarios: 'Temporary scenario calculations exist through the forecast API. Saved scenario management remains future scope.' };

function money(value) {
  if (value === null || value === undefined || value === '') return 'Pending';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value || 0));
}
function signed(value) {
  const n = Number(value || 0);
  const formatted = money(Math.abs(n));
  return `${n >= 0 ? '+' : '-'}${formatted}`;
}
function amountClass(value) { return Number(value || 0) >= 0 ? 'positive' : 'negative'; }
function iso(d) { return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function firstOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function daysInMonth(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate(); }
function dateLabel(value) { return new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)); }
function monthLabel(value) { return new Intl.DateTimeFormat('en-AU', { month: 'long', year: 'numeric' }).format(value); }
function Field({ label, ...props }) { return <label className="field"><span>{label}</span><input {...props} /></label>; }
function Empty({ title, children }) { return <div className="empty"><strong>{title}</strong><p>{children}</p></div>; }
function Badge({ children, tone = '' }) { return <span className={`badge ${tone}`}>{children}</span>; }
function Icon({ children }) { return <span className="nav-icon" aria-hidden="true">{children}</span>; }

function summariseForecast(forecast) {
  const rows = forecast?.timeline || [];
  const income = rows.filter((r) => r.direction === 'income').reduce((sum, r) => sum + Number(r.amount || 0), 0);
  const recurring = rows.filter((r) => ['recurring_expense', 'bill'].includes(r.source_type)).reduce((sum, r) => sum + Number(r.amount || 0), 0);
  const planned = rows.filter((r) => r.source_type === 'planned_spending').reduce((sum, r) => sum + Number(r.amount || 0), 0);
  const estimated = rows.filter((r) => r.estimated).reduce((sum, r) => sum + Number(r.amount || 0), 0);
  return { income, recurring, planned, estimated };
}

function Chart({ baseline, expected }) {
  const buildPoints = (forecast) => {
    const rows = [{ date: forecast?.start_date || today, forecast_balance: forecast?.starting_balance || '0.00' }, ...(forecast?.timeline || [])];
    return rows.map((r, i) => ({ x: i, y: Number(r.forecast_balance || 0), label: r.date }));
  };
  const base = buildPoints(baseline);
  const exp = buildPoints(expected);
  const all = [...base, ...exp];
  if (!all.length) return <Empty title="No forecast available">Add balances, income and commitments to see the projection.</Empty>;
  const min = Math.min(...all.map((p) => p.y));
  const max = Math.max(...all.map((p) => p.y));
  const spread = Math.max(max - min, 1);
  const toPath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'} ${(p.x / Math.max(pts.length - 1, 1)) * 100} ${70 - ((p.y - min) / spread) * 55}`).join(' ');
  return <div className="chart" role="img" aria-label="Cash flow forecast chart"><svg viewBox="0 0 100 80" preserveAspectRatio="none"><path className="gridline" d="M0 15 H100 M0 42 H100 M0 70 H100"/><path className="baseline-line" d={toPath(base)} /><path className="expected-line" d={toPath(exp)} /></svg><div className="chart-legend"><span><i className="dot baseline"/>Baseline Forecast</span><span><i className="dot expected"/>Expected Forecast</span><span><i className="dot danger"/>Lowest Balance</span></div></div>;
}

function Sidebar({ active, setActive }) {
  const button = (item) => <button key={item} onClick={() => setActive(item)} className={active === item ? 'active' : ''}><Icon>{navIcon(item)}</Icon>{item}{futurePages[item] && <small>Upcoming</small>}</button>;
  return <aside className="sidebar"><div className="brand"><img src={mark} alt=""/><div><strong>Fynvo</strong><small>Know what's coming.</small></div></div><nav><p>Core</p>{coreNav.map(button)}<p>Analysis</p>{analysisNav.map(button)}<p>Settings</p>{settingsNav.map(button)}</nav><div className="user-card"><span>SP</span><div><strong>Stu P</strong><small>Household</small></div></div></aside>;
}
function navIcon(item) { return ({ Overview:'⌂', 'Cash Flow':'↗', Calendar:'□', Accounts:'▣', Transactions:'⇄', 'Recurring Expenses':'↻', Income:'+$', Bills:'▤', 'Planned Spending':'🛒', Budgeting:'%', Reports:'▥', Insights:'✦', Scenarios:'⌘', Categories:'⚙', Settings:'⚙' })[item] || '•'; }

export default function App() {
  const [auth, setAuth] = useState(null);
  const [active, setActive] = useState(localStorage.getItem('fynvo.view') || 'Overview');
  const [error, setError] = useState('');
  const [form, setForm] = useState({ username: '', display_name: '', password: '' });
  const [data, setData] = useState({ accounts: [], transactions: [], income: [], recurring: [], bills: [], planned: [] });
  const [overview, setOverview] = useState(null);
  const [horizon, setHorizon] = useState('90d');
  const [baseline, setBaseline] = useState(null);
  const [expected, setExpected] = useState(null);
  const [calendar, setCalendar] = useState({ view: 'month', cursor: new Date(), forecast: null });
  const [modal, setModal] = useState(null);
  const [quick, setQuick] = useState(null);
  const [quickForm, setQuickForm] = useState({ type: 'transaction', name: '', amount: '', date: today, category: '', account_id: '', frequency: 'monthly' });

  async function loadAuth() { const res = await api('/auth/state'); setAuth(await res.json()); }
  async function loadData(nextHorizon = horizon) {
    const [overviewRes, accountsRes, txRes, incomeRes, recRes, billsRes, plannedRes, baseRes, expRes] = await Promise.all([
      api('/dashboard/overview'), api('/accounts'), api('/transactions'), api('/income'), api('/recurring-expenses'), api('/bills'), api('/planned-spending'), api(`/forecast?horizon=${nextHorizon}&mode=baseline`), api(`/forecast?horizon=${nextHorizon}&mode=expected`),
    ]);
    if (overviewRes.ok) setOverview(await overviewRes.json());
    setData({ accounts: accountsRes.ok ? await accountsRes.json() : [], transactions: txRes.ok ? await txRes.json() : [], income: incomeRes.ok ? await incomeRes.json() : [], recurring: recRes.ok ? await recRes.json() : [], bills: billsRes.ok ? await billsRes.json() : [], planned: plannedRes.ok ? await plannedRes.json() : [] });
    if (baseRes.ok) setBaseline(await baseRes.json());
    if (expRes.ok) setExpected(await expRes.json());
  }
  async function loadCalendar(view = calendar.view, cursor = calendar.cursor) {
    const start = view === 'month' ? firstOfMonth(cursor) : view === 'week' ? addDays(cursor, -cursor.getDay()) : cursor;
    const days = view === 'month' ? daysInMonth(cursor) + 6 : view === 'week' ? 7 : 1;
    const res = await api(`/forecast?mode=expected&start=${iso(start)}&horizon=${days}d`);
    if (res.ok) setCalendar({ view, cursor, forecast: await res.json() });
  }
  useEffect(() => { loadAuth(); }, []);
  useEffect(() => { if (auth?.authenticated) loadData(); }, [auth?.authenticated]);
  useEffect(() => { localStorage.setItem('fynvo.view', active); if (auth?.authenticated && active === 'Calendar') loadCalendar(); }, [active, auth?.authenticated]);
  useEffect(() => { if (auth?.authenticated) loadData(horizon); }, [horizon]);

  async function submitAuth(e) { e.preventDefault(); setError(''); const endpoint = auth?.setup_required ? '/auth/setup' : '/auth/login'; const payload = auth?.setup_required ? { username: form.username, display_name: form.display_name || form.username, password: form.password } : { username: form.username, password: form.password }; const res = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) }); if (!res.ok) { setError('Sign-in failed. Check the username and password.'); return; } await loadAuth(); }
  async function logout() { await api('/auth/logout', { method: 'POST' }); setAuth({ authenticated: false, setup_required: false, user: null }); }
  async function saveQuick(e) {
    e.preventDefault();
    const f = quickForm;
    const payloads = {
      transaction: ['/transactions', { account_id: Number(f.account_id), date: f.date, amount: f.amount, transaction_type: Number(f.amount) >= 0 ? 'income' : 'expense', description: f.name, category: f.category }],
      income: ['/income', { name: f.name, amount: f.amount, frequency: f.frequency, next_payment_date: f.date, category: f.category }],
      recurring: ['/recurring-expenses', { name: f.name, amount: f.amount, frequency: f.frequency, next_due_date: f.date, category: f.category }],
      bill: ['/bills', { name: f.name, amount: f.amount, due_date: f.date, bill_type: f.category, priority: 'normal' }],
      planned: ['/planned-spending', { name: f.name, estimated_amount: f.amount, planned_date: f.date, category: f.category, status: 'planned', include_in_forecast: true }],
    };
    const [path, payload] = payloads[f.type];
    const res = await api(path, { method: 'POST', body: JSON.stringify(payload) });
    if (res.ok) { setQuick(null); setQuickForm({ type: 'transaction', name: '', amount: '', date: today, category: '', account_id: '', frequency: 'monthly' }); await loadData(); if (active === 'Calendar') await loadCalendar(); } else setError('Quick Add could not save. Check required fields.');
  }

  if (!auth) return <main className="login"><div className="login-card"><img className="login-logo" src={logo} alt="Fynvo"/><p>Loading...</p></div></main>;
  if (!auth.authenticated) return <main className="login"><form className="login-card" onSubmit={submitAuth}><img className="login-logo" src={logo} alt="Fynvo"/><p>Know what's coming.</p>{auth.setup_required && <p className="notice">Create the first administrator account.</p>}<Field label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}/>{auth.setup_required && <Field label="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}/>}<Field label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}/>{error && <p className="error">{error}</p>}<button className="primary">{auth.setup_required ? 'Create account' : 'Sign in'}</button></form></main>;

  return <div className="shell"><Sidebar active={active} setActive={setActive}/><main className="content"><header className="header"><div><p className="eyebrow">Household finance</p><h1>{active === 'Overview' ? `Good morning, ${auth.user?.display_name || 'Stu'}!` : active}</h1><p>Here's your financial overview and what's ahead.</p></div><div className="header-actions"><label className="range"><span>Date range</span><select value={horizon} onChange={(e) => setHorizon(e.target.value)}>{ranges.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label><button className="primary ghost" onClick={() => setQuick(true)}>+ Quick Add</button><button onClick={logout}>Logout</button></div></header>{error && <p className="error banner">{error}</p>}
    {active === 'Overview' && <Overview overview={overview} baseline={baseline} expected={expected} data={data} setActive={setActive} setModal={setModal}/>} 
    {active === 'Cash Flow' && <CashFlow baseline={baseline} expected={expected} setModal={setModal}/>} 
    {active === 'Calendar' && <Calendar calendar={calendar} loadCalendar={loadCalendar} setModal={setModal}/>} 
    {active === 'Categories' && <Categories data={data}/>} 
    {futurePages[active] && <Future title={active}>{futurePages[active]}</Future>} 
    {!['Overview','Cash Flow','Calendar','Categories', ...Object.keys(futurePages)].includes(active) && <SimpleModule active={active} data={data}/>} 
  </main>{modal && <EventModal event={modal} onClose={() => setModal(null)}/>} {quick && <QuickAdd form={quickForm} setForm={setQuickForm} accounts={data.accounts} onSubmit={saveQuick} onClose={() => setQuick(null)}/>}</div>;
}

function Overview({ overview, baseline, expected, data, setActive, setModal }) {
  const b = summariseForecast(baseline); const e = summariseForecast(expected);
  const upcoming = (expected?.timeline || []).slice(0, 6);
  return <><section className="kpi-grid"><Kpi icon="💵" label="Available Cash" value={overview?.summary?.available_cash}/><Kpi icon="↗" label="Expected Income" value={b.income}/><Kpi icon="▤" label="Scheduled Commitments" value={b.recurring}/><Kpi icon="🛒" label="Planned Spending" value={b.planned}/><Kpi icon="↗" label="Projected Balance" value={baseline?.final_balance}/></section><section className="dashboard-grid"><article className="panel forecast-panel"><div className="panel-head"><h2>Cash Flow Forecast</h2><button onClick={() => setActive('Cash Flow')}>View full cash flow →</button></div><Chart baseline={baseline} expected={expected}/><div className="forecast-summary-strip"><SummaryCell label="End of 30 days" value={baseline?.final_balance}/><SummaryCell label="Lowest Balance" value={baseline?.lowest_balance?.balance} tone={Number(baseline?.lowest_balance?.balance || 0) < 0 ? 'negative' : ''}/><SummaryCell label="End of selected range" value={baseline?.final_balance}/>{baseline?.shortfall && <div className="shortfall"><strong>⚠ Cash shortfall risk</strong><span>Projected on {dateLabel(baseline.shortfall.date)}</span><b>{money(baseline.shortfall.balance)}</b></div>}</div></article><article className="panel"><h2>Forecast Summary</h2><SummaryRow label="Baseline Forecast" value={baseline?.final_balance}/><SummaryRow label="Expected Forecast" value={expected?.final_balance}/><SummaryRow label="Estimated spending" value={e.estimated}/><button className="link" onClick={() => setActive('Cash Flow')}>View forecast →</button></article><article className="panel"><h2>Upcoming Commitments</h2><EventList rows={upcoming} setModal={setModal}/><button className="link" onClick={() => setActive('Calendar')}>View calendar →</button></article><article className="panel"><h2>Top Planned Spending</h2>{data.planned?.length ? data.planned.slice(0,4).map((p) => <div className="mini-row" key={p.id}><span>{p.name}<small>{p.planned_date ? dateLabel(p.planned_date) : 'Date pending'}</small></span><strong>{money(p.estimated_amount)}</strong></div>) : <Empty title="No Planned Spending yet">Add future purchases or financial plans to include them in your forecast.</Empty>}</article><article className="panel"><h2>Quick Stats</h2>{overview?.quick_stats?.map((s, i) => <SummaryRow key={i} label={s.label} value={s.value}/>)}</article></section></>;
}
function Kpi({ icon, label, value }) { return <article className="kpi"><span className="kpi-icon">{icon}</span><div><span>{label}</span><strong>{money(value)}</strong></div></article>; }
function SummaryCell({ label, value, tone='' }) { return <div><span>{label}</span><strong className={tone}>{money(value)}</strong></div>; }
function SummaryRow({ label, value }) { return <div className="summary-row"><span>{label}</span><strong className={amountClass(value)}>{money(value)}</strong></div>; }
function EventList({ rows = [], setModal }) { if (!rows.length) return <Empty title="No upcoming commitments">Nothing scheduled during this period.</Empty>; return <div className="event-list">{rows.map((r, i) => <button key={`${r.date}-${r.name}-${i}`} onClick={() => setModal(r)}><span className="date-pill"><b>{new Date(r.date).getDate()}</b><small>{new Date(r.date).toLocaleString('en-AU',{month:'short'})}</small></span><span>{r.name}<small>{r.category} · {r.source_type}</small></span><strong className={amountClass(r.amount)}>{money(r.amount)}</strong></button>)}</div>; }

function CashFlow({ baseline, expected, setModal }) { const rows = baseline?.timeline || []; return <><section className="kpi-grid"><Kpi icon="•" label="Starting Balance" value={baseline?.starting_balance}/><Kpi icon="↗" label="Projected Balance" value={baseline?.final_balance}/><Kpi icon="⚠" label="Lowest Balance" value={baseline?.lowest_balance?.balance}/><Kpi icon="~" label="Expected Forecast" value={expected?.final_balance}/></section><section className="panel"><h2>Cash Flow Projection</h2><Chart baseline={baseline} expected={expected}/></section><section className="panel"><h2>Forecast Timeline</h2><div className="table"><div className="thead"><span>Date</span><span>Item</span><span>Type</span><span>Amount</span><span>Forecast Balance</span></div>{rows.map((r,i) => <button className="tr five" key={i} onClick={() => setModal(r)}><span>{dateLabel(r.date)}</span><span>{r.name}<small>{r.category}</small></span><span><Badge>{r.source_type}</Badge>{r.estimated && <Badge tone="warn">Estimated</Badge>}</span><strong className={amountClass(r.amount)}>{money(r.amount)}</strong><strong>{money(r.forecast_balance)}</strong></button>)}</div></section></>; }

function Calendar({ calendar, loadCalendar, setModal }) {
  const rows = calendar.forecast?.timeline || [];
  const grouped = rows.reduce((acc, r) => { (acc[r.date] ||= []).push(r); return acc; }, {});
  const start = calendar.view === 'month' ? firstOfMonth(calendar.cursor) : calendar.view === 'week' ? addDays(calendar.cursor, -calendar.cursor.getDay()) : calendar.cursor;
  const days = calendar.view === 'month' ? Array.from({length: daysInMonth(calendar.cursor)}, (_, i) => addDays(start, i)) : calendar.view === 'week' ? Array.from({length:7}, (_,i)=>addDays(start,i)) : [calendar.cursor];
  const move = (n) => { const c = new Date(calendar.cursor); calendar.view === 'month' ? c.setMonth(c.getMonth()+n) : c.setDate(c.getDate()+n*(calendar.view==='week'?7:1)); loadCalendar(calendar.view, c); };
  return <section className="panel"><div className="panel-head"><div><h2>Financial Calendar</h2><p className="muted">Unified future income, bills, recurring expenses, Planned Spending and forecast estimates.</p></div><div className="segmented"><button onClick={() => loadCalendar('day', calendar.cursor)} className={calendar.view==='day'?'active':''}>Day</button><button onClick={() => loadCalendar('week', calendar.cursor)} className={calendar.view==='week'?'active':''}>Week</button><button onClick={() => loadCalendar('month', calendar.cursor)} className={calendar.view==='month'?'active':''}>Month</button></div></div><div className="calendar-controls"><button onClick={() => move(-1)}>←</button><strong>{calendar.view === 'month' ? monthLabel(calendar.cursor) : dateLabel(iso(calendar.cursor))}</strong><button onClick={() => move(1)}>→</button><button onClick={() => loadCalendar(calendar.view, new Date())}>Today</button></div><div className={`calendar ${calendar.view}`}>{days.map((d) => <article key={iso(d)} className={iso(d)===today?'today':''}><header><strong>{d.getDate()}</strong><span>{d.toLocaleString('en-AU',{weekday:'short'})}</span></header>{(grouped[iso(d)] || []).slice(0,5).map((r,i) => <button key={i} className={`cal-event ${r.direction}`} onClick={() => setModal(r)}><span>{r.name}</span><strong>{signed(r.amount)}</strong><small>{r.source_type}{r.estimated ? ' · estimated' : ''}</small></button>)}</article>)}</div></section>;
}

function Categories({ data }) {
  const categories = useMemo(() => { const map = new Map(); const add = (name, source) => { if (!name) return; const row = map.get(name) || { name, sources: new Set(), count: 0 }; row.sources.add(source); row.count += 1; map.set(name, row); }; data.transactions.forEach(x => add(x.category, 'Transactions')); data.recurring.forEach(x => add(x.category, 'Recurring')); data.income.forEach(x => add(x.category, 'Income')); data.bills.forEach(x => add(x.bill_type, 'Bills')); data.planned.forEach(x => add(x.category, 'Planned')); return [...map.values()].map(x => ({...x, sources:[...x.sources]})).sort((a,b)=>a.name.localeCompare(b.name)); }, [data]);
  return <section className="panel"><h2>Categories</h2><p className="muted">v0.7.0 unifies category visibility across Fynvo without corrupting historical records. Full hierarchy editing expands in the budgeting/reporting releases.</p>{categories.length ? <div className="category-grid">{categories.map((c) => <article key={c.name} className="category-card"><span className="cat-icon">◦</span><strong>{c.name}</strong><small>{c.sources.join(', ')}</small><Badge>{c.count} records</Badge></article>)}</div> : <Empty title="No categories yet">Categories appear as financial records are created.</Empty>}</section>;
}
function SimpleModule({ active, data }) { const map = { Accounts:data.accounts, Transactions:data.transactions, Income:data.income, 'Recurring Expenses':data.recurring, Bills:data.bills, 'Planned Spending':data.planned }; const rows = map[active] || []; return <section className="panel"><h2>{active}</h2>{rows.length ? <div className="table">{rows.map((r,i) => <div className="tr" key={i}><span>{r.date || r.transaction_date || r.next_due_date || r.next_payment_date || r.due_date || r.planned_date || '—'}</span><span>{r.name || r.description}<small>{r.category || r.bill_type || r.account_type || ''}</small></span><strong className={amountClass(r.amount || r.estimated_amount || r.current_balance)}>{money(r.amount || r.estimated_amount || r.current_balance)}</strong><Badge>{r.status || r.frequency || r.source || 'Active'}</Badge></div>)}</div> : <Empty title={`No ${active.toLowerCase()} yet`}>Use Quick Add to create the first record.</Empty>}</section>; }
function Future({ title, children }) { return <section className="panel"><Badge tone="warn">Upcoming</Badge><h2>{title}</h2><p>{children}</p><Empty title="Foundation ready">Navigation and design-system space has been reserved without pretending this future feature is complete.</Empty></section>; }
function EventModal({ event, onClose }) { return <div className="modal-backdrop" role="dialog" aria-modal="true"><div className="modal"><button className="close" onClick={onClose}>×</button><h2>{event.name}</h2><div className="detail-grid"><SummaryRow label="Date" value={event.date}/><SummaryRow label="Amount" value={event.amount}/><SummaryRow label="Forecast balance" value={event.forecast_balance}/><SummaryRow label="Type" value={event.source_type}/><SummaryRow label="Category" value={event.category}/><SummaryRow label="Classification" value={event.financial_layer || event.confidence}/></div><p className="muted">{event.explanation || 'Projected financial event generated from Fynvo records.'}</p></div></div>; }
function QuickAdd({ form, setForm, accounts, onSubmit, onClose }) { return <div className="modal-backdrop" role="dialog" aria-modal="true"><form className="modal" onSubmit={onSubmit}><button type="button" className="close" onClick={onClose}>×</button><h2>Quick Add</h2><label className="field"><span>Type</span><select value={form.type} onChange={(e)=>setForm({...form,type:e.target.value})}><option value="transaction">Transaction</option><option value="income">Income</option><option value="recurring">Recurring Expense</option><option value="bill">Bill</option><option value="planned">Planned Spending</option></select></label><Field label="Name" value={form.name} onChange={(e)=>setForm({...form,name:e.target.value})}/><Field label="Amount" value={form.amount} onChange={(e)=>setForm({...form,amount:e.target.value})}/><Field label="Date" type="date" value={form.date} onChange={(e)=>setForm({...form,date:e.target.value})}/><Field label="Category" value={form.category} onChange={(e)=>setForm({...form,category:e.target.value})}/>{form.type==='transaction' && <label className="field"><span>Account</span><select value={form.account_id} onChange={(e)=>setForm({...form,account_id:e.target.value})}><option value="">Select account</option>{accounts.map((a)=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label>}{['income','recurring'].includes(form.type) && <label className="field"><span>Frequency</span><select value={form.frequency} onChange={(e)=>setForm({...form,frequency:e.target.value})}><option value="weekly">Weekly</option><option value="fortnightly">Fortnightly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="yearly">Yearly</option></select></label>}<button className="primary">Save</button></form></div>; }
