import { useEffect, useRef, useState } from 'react';
import InsightsPage from './InsightsPage.jsx';
import logo from './assets/fynvo-logo.svg';
import mark from './assets/fynvo-mark.svg';
import './styles.css';

const api = (path, options = {}) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
const today = new Date().toISOString().slice(0, 10);
const navGroups = [
  { label: 'Core', items: ['Overview', 'Cash Flow', 'Calendar', 'Accounts'] },
  { label: 'Money', items: ['Transactions', 'Income', 'Bills', 'Recurring Expenses', 'Planned Spending'] },
  { label: 'Planning', items: ['Budgeting', 'Goals'] },
  { label: 'Intelligence', items: ['Insights', 'Spending Intelligence'] },
  { label: 'Import & Data', items: ['CSV Import', 'Import History', 'Review Queue', 'Categories'] },
];
const accountTypeOptions = [
  ['transaction', 'Transaction Account'], ['savings', 'Savings Account'], ['offset', 'Offset Account'], ['credit_card', 'Credit Card'], ['cash', 'Cash'], ['mortgage', 'Mortgage'], ['personal_loan', 'Personal Loan'], ['car_loan', 'Car Loan'], ['line_of_credit', 'Line of Credit'], ['investment', 'Investment Account'], ['superannuation', 'Superannuation'], ['other_asset', 'Other Asset'], ['other_liability', 'Other Liability'],
];
const accountTypeLabel = (value) => accountTypeOptions.find(([id]) => id === value)?.[1] || (value === 'vehicle_loan' ? 'Car Loan' : value?.replaceAll('_', ' ') || 'Account');
const horizonOptions = [
  { label: 'Next 7 days', value: 7 },
  { label: 'Next 30 days', value: 30 },
  { label: 'Next 90 days', value: 90 },
  { label: 'Next 6 months', value: 184 },
  { label: 'Next 12 months', value: 365 },
];
const money = (value) => value === null || value === undefined || value === '' ? '$0.00' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value || 0));
const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`)) : 'No date';
const amountClass = (value) => Number(value || 0) >= 0 ? 'positive' : 'negative';
const parseAmount = (value) => Number(value || 0);
const Field = ({ label, children, error, ...props }) => <label className={`field ${error ? 'field-error' : ''}`}><span>{label}</span>{children || <input {...props}/>} {error && <small className="field-error-message">{error}</small>}</label>;
const Badge = ({ children, tone = '' }) => <span className={`badge ${tone}`}>{children}</span>;
const Empty = ({ title, children, action }) => <div className="empty"><strong>{title}</strong><p>{children}</p>{action}</div>;
const toDateInput = (value) => value ? String(value).slice(0, 10) : '';

function friendlyError(payload, fallback) {
  const detail = payload?.detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const field = item.loc?.slice(-1)[0];
      if (field === 'account_id' || field === 'destination_account_id') return 'Choose a valid account.';
      if (item.type === 'missing') return `${String(field || 'A required field').replaceAll('_', ' ')} is required.`;
      if (field) return `Check ${String(field).replaceAll('_', ' ')}.`;
      return null;
    }).filter(Boolean);
    return [...new Set(messages)].join(' ') || fallback;
  }
  if (typeof detail === 'string') return detail;
  return fallback;
}

function normaliseRecord(type, row = {}) {
  if (type === 'accounts') return { name: row.name || '', account_type: row.account_type || 'transaction', institution: row.institution || '', opening_balance: row.opening_balance || '0.00', description: row.description || '', account_suffix: row.account_suffix || '', icon: row.icon || '', color: row.color || '' };
  if (type === 'transactions') return { account_id: row.account_id || '', date: toDateInput(row.date || row.transaction_date) || today, amount: row.amount || '', transaction_type: row.transaction_type || 'expense', description: row.description || '', merchant: row.merchant || '', category: row.category || '', notes: row.notes || '', status: row.status || 'cleared' };
  if (type === 'income') return { name: row.name || '', amount: row.amount || '', frequency: row.frequency || 'monthly', next_payment_date: toDateInput(row.next_payment_date) || today, destination_account_id: row.destination_account_id || '', payer: row.payer || '', category: row.category || '', is_active: row.is_active ?? true, notes: row.notes || '', effective_from: '' };
  if (type === 'recurring') return { name: row.name || '', amount: row.amount || '', frequency: row.frequency || 'monthly', next_due_date: toDateInput(row.next_due_date) || today, account_id: row.account_id || '', source_account_text: row.source_account_text || '', category: row.category || '', expense_type: row.expense_type || '', is_active: row.is_active ?? true, variable_amount: row.variable_amount ?? false, direct_debit: row.direct_debit ?? false, notes: row.notes || '', effective_from: '' };
  if (type === 'bills') return { name: row.name || '', provider: row.provider || '', bill_type: row.bill_type || '', priority: row.priority || 'normal', amount: row.amount || '', due_date: toDateInput(row.due_date) || today, account_id: row.account_id || '', paid_through_date: toDateInput(row.paid_through_date), status: row.status || '', notes: row.notes || '', recurring_expense_id: row.recurring_expense_id || '' };
  if (type === 'planned') return { name: row.name || '', description: row.description || '', estimated_amount: row.estimated_amount || '', planned_date: toDateInput(row.planned_date) || today, category: row.category || '', account_id: row.account_id || '', merchant: row.merchant || '', priority: row.priority || 'medium', status: row.status || 'planned', include_in_forecast: row.include_in_forecast ?? true, notes: row.notes || '' };
  if (type === 'categories') return { name: row.name || '', parent_id: row.parent_id || '', icon: row.icon || '', color: row.color || '', category_type: row.category_type || 'expense', budget_relationship: row.budget_relationship || 'independent', is_active: row.is_active ?? true, notes: row.notes || '' };
  if (type === 'budgets') return { name: row.name || '', category_id: row.category_id || '', category_name: row.category_name || '', direction: row.direction || 'expense', period: row.period || 'monthly', amount: row.amount || '', allocation_strategy: row.allocation_strategy || 'spend_during_period', relationship_mode: row.relationship_mode || 'independent', anchor_date: toDateInput(row.anchor_date) || today, start_date: toDateInput(row.start_date) || today, end_date: toDateInput(row.end_date), rollover_enabled: row.rollover_enabled ?? false, negative_rollover_enabled: row.negative_rollover_enabled ?? false, is_active: row.is_active ?? true, notes: row.notes || '', effective_from: '' };
  if (type === 'goals') return { name: row.name || '', description: row.description || '', goal_type: row.goal_type || 'savings', target_amount: row.target_amount || '', current_amount: row.current_amount || '', start_date: toDateInput(row.start_date) || today, target_date: toDateInput(row.target_date), priority: row.priority || 'medium', contribution_frequency: row.contribution_frequency || 'monthly', contribution_amount: row.contribution_amount || '', status: row.status || 'active', notes: row.notes || '' };
  return { ...row };
}

function endpointFor(type, id) {
  return ({ accounts: `/accounts/${id}`, transactions: `/transactions/${id}`, income: `/income/${id}`, recurring: `/recurring-expenses/${id}`, bills: `/bills/${id}`, planned: `/planned-spending/${id}`, categories: `/categories/${id}`, budgets: `/budgets/${id}`, goals: `/goals/${id}` })[type];
}

function createPath(type) {
  return ({ accounts: '/accounts', transactions: '/transactions', income: '/income', recurring: '/recurring-expenses', bills: '/bills', planned: '/planned-spending', categories: '/categories', budgets: '/budgets', goals: '/goals' })[type];
}

export default function App() {
  const [auth, setAuth] = useState(null);
  const [active, setActive] = useState(localStorage.getItem('fynvo.view') || 'Overview');
  const [rangeDays, setRangeDays] = useState(Number(localStorage.getItem('fynvo.rangeDays') || 90));
  const [form, setForm] = useState({ username: '', display_name: '', password: '' });
  const [data, setData] = useState({ accounts: [], transactions: [], income: [], recurring: [], bills: [], planned: [], categories: [], budgets: [], goals: [], imports: [], review: [], suggestions: [], insights: [], financialHealth: null, budgetAnalysis: null, forecast: null, command: null });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [edit, setEdit] = useState(null);
  const [quick, setQuick] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const menuButtonRef = useRef(null);
  const closeButtonRef = useRef(null);
  const [importState, setImportState] = useState({ filename: '', account_id: '', csv_text: '', source_name: 'Australian bank CSV', mapping: { date: 'Date', description: 'Description', debit: 'Debit', credit: 'Credit', amount: 'Amount' }, preview: null });

  async function loadAuth() { const res = await api('/auth/state'); setAuth(await res.json()); }
  async function j(path) { const res = await api(path); return res.ok ? await res.json() : null; }
  async function loadData() {
    const [command, accounts, transactions, income, recurring, bills, planned, categories, budgets, goals, imports, review, suggestions, insights, financialHealth, budgetAnalysis, forecast] = await Promise.all([
      j(`/dashboard/command-centre?range_days=${rangeDays}`), j('/accounts'), j('/transactions'), j('/income'), j('/recurring-expenses'), j('/bills'), j('/planned-spending'), j('/categories'), j('/budgets'), j('/goals'), j('/imports/history'), j('/reconciliation/review-queue'), j('/intelligence/suggestions'), j(`/insights?horizon_days=${rangeDays}&refresh=false`), j(`/insights/financial-health?horizon_days=${rangeDays}`), j('/budgets/analysis'), j(`/forecast?mode=expected&horizon=${rangeDays}d`),
    ]);
    setData({ command, accounts: accounts || [], transactions: transactions || [], income: income || [], recurring: recurring || [], bills: bills || [], planned: planned || [], categories: categories || [], budgets: budgets || [], goals: goals || [], imports: imports || [], review: review || [], suggestions: suggestions || [], insights: insights || [], financialHealth, budgetAnalysis, forecast });
  }
  useEffect(() => { loadAuth(); }, []);
  useEffect(() => { if (auth?.authenticated) loadData(); }, [auth?.authenticated, rangeDays]);
  useEffect(() => { localStorage.setItem('fynvo.view', active); }, [active]);
  useEffect(() => { localStorage.setItem('fynvo.rangeDays', String(rangeDays)); }, [rangeDays]);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 980px)');
    const sync = (event) => {
      setIsMobile(event.matches);
      setMobileNavOpen(false);
      document.body.style.overflow = '';
    };
    media.addEventListener?.('change', sync);
    return () => media.removeEventListener?.('change', sync);
  }, []);
  useEffect(() => {
    if (!isMobile) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = mobileNavOpen ? 'hidden' : previousOverflow;
    if (mobileNavOpen) window.requestAnimationFrame(() => closeButtonRef.current?.focus({ preventScroll: true }));
    return () => { document.body.style.overflow = previousOverflow; };
  }, [mobileNavOpen, isMobile]);
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape' && mobileNavOpen) {
        event.preventDefault();
        setMobileNavOpen(false);
        window.requestAnimationFrame(() => menuButtonRef.current?.focus({ preventScroll: true }));
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [mobileNavOpen]);

  async function submitAuth(e) { e.preventDefault(); setError(''); const payload = auth?.setup_required ? { username: form.username, display_name: form.display_name || form.username, password: form.password } : { username: form.username, password: form.password }; const res = await api(auth?.setup_required ? '/auth/setup' : '/auth/login', { method: 'POST', body: JSON.stringify(payload) }); if (res.ok) { setMobileNavOpen(false); await loadAuth(); } else setError('Sign-in failed. Check your username and password.'); }
  async function logout() { await api('/auth/logout', { method: 'POST' }); setMobileNavOpen(false); setAuth({ authenticated: false, setup_required: false, user: null }); }
  async function saveEdit(e) {
    e.preventDefault(); setError(''); setSuccess('');
    const creating = edit.row?.id === null || edit.row?.id === undefined;
    const path = creating ? createPath(edit.type) : endpointFor(edit.type, edit.row.id);
    const res = await api(path, { method: creating ? 'POST' : 'PUT', body: JSON.stringify(edit.values) });
    if (!res.ok) { setError(friendlyError(await res.json().catch(() => null), `Could not ${creating ? 'create' : 'save'} ${edit.label}. Check the fields and try again.`)); return; }
    setEdit(null);
    setSuccess(`${creating ? edit.label.replace(/^New /, '') + ' created.' : edit.label + ' updated.'}`);
    await loadData();
  }
  async function createRecord(type, values) { setError(''); setSuccess(''); const res = await api(createPath(type), { method: 'POST', body: JSON.stringify(values) }); if (res.ok) { setQuick(null); setSuccess(`${type === 'goals' ? 'Goal' : 'Record'} created.`); await loadData(); } else setError(friendlyError(await res.json().catch(() => null), 'Could not create this record. Check the fields and try again.')); }
  async function previewImport(e) { e.preventDefault(); const res = await api('/imports/preview', { method: 'POST', body: JSON.stringify(importState) }); if (res.ok) setImportState({ ...importState, preview: await res.json() }); else setError('CSV preview failed. Check the account, headers and mapping.'); }
  async function commitImport() { const res = await api('/imports/commit', { method: 'POST', body: JSON.stringify(importState) }); if (res.ok) { setImportState({ ...importState, preview: await res.json() }); await loadData(); } else setError('CSV import failed. Review invalid rows and duplicates.'); }
  async function acceptMatch(id) { const res = await api(`/reconciliation/${id}/accept`, { method: 'POST' }); if (res.ok) await loadData(); else setError('Could not accept match.'); }
  async function completeGoal(id) { const res = await api(`/goals/${id}/complete`, { method: 'POST' }); if (res.ok) { setSuccess('Goal completed.'); await loadData(); } }
  async function dismissSuggestion(id) { const res = await api(`/intelligence/suggestions/${id}/dismiss`, { method: 'POST' }); if (res.ok) await loadData(); }
  async function dismissInsight(id) { const res = await api(`/insights/${id}/dismiss`, { method: 'POST' }); if (res.ok) await loadData(); else setError('Could not dismiss Insight.'); }
  async function reviewInsight(id) { const res = await api(`/insights/${id}/reviewed`, { method: 'POST' }); if (res.ok) await loadData(); else setError('Could not mark Insight as reviewed.'); }
  async function refreshInsights() { const res = await api(`/insights/refresh?horizon_days=${rangeDays}`, { method: 'POST' }); if (res.ok) { setSuccess('Financial Insights refreshed.'); await loadData(); } else setError('Could not refresh Financial Insights.'); }

  const quickDefaults = (type) => ({ type, values: normaliseRecord(type, { account_id: data.accounts[0]?.id || '', destination_account_id: data.accounts[0]?.id || '' }) });
  const navigate = (item) => {
    setActive(item);
    if (isMobile) {
      setMobileNavOpen(false);
      window.requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: 'auto' }));
    }
  };
  const closeMobileNav = (restoreFocus = true) => {
    setMobileNavOpen(false);
    if (restoreFocus) window.requestAnimationFrame(() => menuButtonRef.current?.focus({ preventScroll: true }));
  };

  if (!auth) return <main className="login"><div className="login-card"><img className="login-logo" src={logo} alt="Fynvo"/><p>Loading...</p></div></main>;
  if (!auth.authenticated) return <main className="login"><form className="login-card" onSubmit={submitAuth}><img className="login-logo" src={logo} alt="Fynvo"/><p>Know what's coming.</p>{auth.setup_required && <p className="notice">Create the first administrator account.</p>}<Field label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}/>{auth.setup_required && <Field label="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}/>}<Field label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}/>{error && <p className="error">{error}</p>}<button className="primary">{auth.setup_required ? 'Create account' : 'Sign in'}</button></form></main>;

  return <div className={`shell ${mobileNavOpen ? 'mobile-nav-open' : ''}`}>
    <aside className="sidebar" id="fynvo-navigation" aria-label="Fynvo navigation" aria-hidden={isMobile && !mobileNavOpen ? 'true' : undefined} inert={isMobile && !mobileNavOpen ? true : undefined}>
      <button ref={closeButtonRef} className="mobile-nav-close" type="button" aria-label="Close Fynvo navigation" onClick={() => closeMobileNav()}>×</button>
      <div className="brand"><img src={mark} alt=""/><div><strong>Fynvo</strong><small>Know what's coming.</small></div></div>
      <nav aria-label="Primary navigation">{navGroups.map((group) => <div className="nav-group" key={group.label}><small>{group.label}</small>{group.items.map((item) => <button key={item} className={active === item ? 'active' : ''} aria-current={active === item ? 'page' : undefined} onClick={() => navigate(item)}>{item}</button>)}</div>)}</nav>
      <div className="user-card"><span>{(auth.user?.display_name || 'SP').slice(0, 2).toUpperCase()}</span><div><strong>{auth.user?.display_name}</strong><small>Household</small></div></div>
    </aside>
    <button className="mobile-nav-backdrop" type="button" aria-label="Close Fynvo navigation" tabIndex={mobileNavOpen ? 0 : -1} onClick={() => closeMobileNav()}></button>
    <main className="content">
      <div className="mobile-app-bar" aria-label="Fynvo application controls"><button ref={menuButtonRef} className="mobile-menu-button" type="button" aria-label={mobileNavOpen ? 'Close Fynvo navigation' : 'Open Fynvo navigation'} aria-expanded={mobileNavOpen} aria-controls="fynvo-navigation" onClick={() => setMobileNavOpen((open) => !open)}><span aria-hidden="true">☰</span><span className="sr-only">Menu</span></button><strong className="mobile-app-identity">Fynvo</strong></div>
      <header className="header"><div><p className="eyebrow">Fynvo v0.17.0</p><h1>{active === 'Overview' ? `Good morning, ${auth.user?.display_name || 'there'}! 👋` : active}</h1><p>{active === 'Overview' ? "Here's your financial overview and what's ahead." : active === 'Insights' ? 'Understand what is changing, why it matters and which data supports it.' : 'Manage household financial records and planning.'}</p></div><div className="header-actions"><label className="select-shell">Date range<select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>{horizonOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><button className="primary ghost" onClick={() => setQuick(quickDefaults('transactions'))}>+ Quick Add</button><button className="logout-action" onClick={logout}>Logout</button></div></header>{error && <p className="error banner">{error}</p>}{success && <p className="success banner">{success}</p>}
      {active === 'Overview' && <Overview data={data} setActive={navigate} rangeDays={rangeDays} setQuick={setQuick} quickDefaults={quickDefaults}/>} 
      {active === 'Cash Flow' && <ForecastPage forecast={data.command?.forecast?.expected || data.forecast}/>} 
      {active === 'Calendar' && <CalendarPage command={data.command}/>} 
      {active === 'CSV Import' && <CsvImport state={importState} setState={setImportState} accounts={data.accounts} previewImport={previewImport} commitImport={commitImport}/>} 
      {active === 'Import History' && <ImportHistory rows={data.imports}/>} 
      {active === 'Review Queue' && <ReviewQueue rows={data.review} acceptMatch={acceptMatch}/>} 
      {active === 'Spending Intelligence' && <SpendingIntelligence suggestions={data.suggestions} dismissSuggestion={dismissSuggestion}/>} 
      {active === 'Insights' && <InsightsPage insights={data.insights} health={data.financialHealth || data.command?.financial_health} onDismiss={dismissInsight} onReviewed={reviewInsight} onNavigate={navigate} onRefresh={refreshInsights}/>} 
      {active === 'Budgeting' && <Budgeting budgets={data.budgets} analysis={data.budgetAnalysis} categories={data.categories} onEdit={(row) => setEdit({ type: 'budgets', label: 'Budget', row, values: normaliseRecord('budgets', row) })}/>} 
      {active === 'Goals' && <GoalsPage goals={data.goals} accounts={data.accounts} onEdit={(row) => setEdit({ type: 'goals', label: 'Goal', row, values: normaliseRecord('goals', row) })} onAdd={() => setQuick(quickDefaults('goals'))} onComplete={completeGoal}/>} 
      {['Accounts','Transactions','Income','Recurring Expenses','Bills','Planned Spending','Categories'].includes(active) && <RecordTable active={active} data={data} onEdit={setEdit}/>} 
    </main>{edit && <EditModal edit={edit} setEdit={setEdit} onSubmit={saveEdit} data={data}/>} {quick && <EditModal edit={{ ...quick, row: { id: null }, label: `New ${quick.type === 'goals' ? 'Goal' : quick.type.slice(0, -1)}` }} setEdit={setQuick} onSubmit={(e) => { e.preventDefault(); createRecord(quick.type, quick.values); }} data={data}/>}</div>;
}

function Overview({ data, setActive, rangeDays, setQuick, quickDefaults }) {
  const command = data.command || {};
  const kpis = command.kpis || {};
  const forecast = command.forecast?.baseline;
  const expected = command.forecast?.expected;
  const goals = command.goals || data.goals || [];
  const planned = command.top_planned_spending || data.planned || [];
  const attention = command.attention || {};
  return <div className="dashboard-page"><section className="kpi-grid five"><Kpi icon="💵" label="Available Cash" value={kpis.available_cash}/><Kpi icon="📈" label="Expected Income" value={kpis.expected_income} hint={`${rangeDays} days`}/><Kpi icon="🧾" label="Scheduled Commitments" value={kpis.scheduled_commitments} hint={`${rangeDays} days`}/><Kpi icon="🛒" label="Planned Spending" value={kpis.planned_spending} hint={`${rangeDays} days`}/><Kpi icon="↗" label="Projected Balance" value={kpis.projected_balance} hint={`End of ${rangeDays} days`}/></section>
    <section className="command-grid"><article className="panel chart-panel"><PanelHead title="Cash Flow Forecast" action="View full cash flow →" onAction={() => setActive('Cash Flow')}/><CashFlowChart baseline={forecast} expected={expected}/><ForecastMetrics forecast={forecast}/></article><article className="panel"><PanelHead title="Forecast Summary" meta={`End of ${rangeDays} days`}/><SummaryRow label="Baseline Forecast" value={command.forecast?.summary?.baseline}/><SummaryRow label="Expected Forecast" value={command.forecast?.summary?.expected}/>{command.forecast?.summary?.lowest_balance && <SummaryRow label="Lowest Balance" value={command.forecast.summary.lowest_balance.balance}/>}<button className="link-button" onClick={() => setActive('Cash Flow')}>View cash flow →</button></article><article className="panel"><PanelHead title="Upcoming Commitments" action="View calendar →" onAction={() => setActive('Calendar')}/><CompactEvents rows={command.upcoming_commitments || []}/></article></section>
    <section className="card-grid"><article className="panel"><PanelHead title="Upcoming" meta="Next 7 days" action="View all →" onAction={() => setActive('Calendar')}/><CompactEvents rows={(command.upcoming || []).slice(0, 4)}/></article><article className="panel"><PanelHead title="Top Planned Spending" action="+ Quick Add" onAction={() => setQuick(quickDefaults('planned'))}/>{planned.length ? planned.slice(0, 4).map((item) => <div className="list-row" key={item.id || item.name}><span>{item.name}<small>{dateLabel(item.planned_date)}</small></span><strong>{money(item.estimated_amount)}</strong></div>) : <Empty title="No planned spending">No planned purchases during this period.</Empty>}<button className="link-button" onClick={() => setActive('Planned Spending')}>View all →</button></article><article className="panel"><PanelHead title="Quick Stats"/><SummaryRow label="Average monthly income" value={command.quick_stats?.average_monthly_income}/><SummaryRow label="Average monthly commitments" value={command.quick_stats?.average_monthly_commitments}/><SummaryRow label="Average monthly planned" value={command.quick_stats?.average_monthly_planned}/><SummaryRow label="Average monthly net forecast" value={command.quick_stats?.average_monthly_net_forecast}/></article></section>
    <section className="card-grid lower"><article className="panel"><PanelHead title="Budget Overview" action="View budgets →" onAction={() => setActive('Budgeting')}/><BudgetSnippet rows={command.budget_overview || []}/></article><article className="panel"><PanelHead title="Goals" action="+ Add goal" onAction={() => setQuick(quickDefaults('goals'))}/>{goals.length ? goals.slice(0, 4).map((goal) => <GoalMini key={goal.id} goal={goal}/>) : <Empty title="No Goals Yet">Create a goal to start planning for a future expense or savings target.<button className="primary ghost" onClick={() => setQuick(quickDefaults('goals'))}>+ Add Goal</button></Empty>}<button className="link-button" onClick={() => setActive('Goals')}>View goals →</button></article><article className="panel attention"><PanelHead title="Financial Health" action="View insights →" onAction={() => setActive('Insights')}/><strong>{attention.headline || 'No major issues detected'}</strong>{attention.top?.length ? <div className="dashboard-insight-list">{attention.top.map((item) => <div className="dashboard-insight-item" key={item.id}><strong>{item.title}</strong><small>{item.importance?.replace('_', ' ')}</small></div>)}</div> : <p>No high-priority financial Insights are active for this period.</p>}</article></section></div>;
}

function Kpi({ icon, label, value, hint }) { return <article className="kpi"><span className="kpi-icon">{icon}</span><div><span>{label}</span><strong className={amountClass(value)}>{typeof value === 'number' ? value : money(value)}</strong>{hint && <small>{hint}</small>}</div></article>; }
function PanelHead({ title, meta, action, onAction }) { return <div className="panel-head compact"><div><h2>{title}</h2>{meta && <small>{meta}</small>}</div>{action && <button className="link-button" onClick={onAction}>{action}</button>}</div>; }
function SummaryRow({ label, value }) { return <div className="summary-row"><span>{label}</span><strong className={amountClass(value)}>{money(value)}</strong></div>; }

function CashFlowChart({ baseline, expected }) {
  const points = baseline?.chart_points || [];
  const expectedPoints = expected?.chart_points || [];
  const all = [...points, ...expectedPoints];
  if (!all.length) return <Empty title="No forecast yet">Add income, recurring expenses, bills or planned spending to generate a forecast.</Empty>;
  const values = all.map((p) => Number(p.balance || 0));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const line = (rows) => rows.map((p, i) => `${(i / Math.max(rows.length - 1, 1)) * 100},${92 - ((Number(p.balance || 0) - min) / Math.max(max - min, 1)) * 78}`).join(' ');
  return <div className="chart-wrap" role="img" aria-label="Cash flow forecast chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="0" y1="92" x2="100" y2="92"/><line x1="0" y1="50" x2="100" y2="50"/><polyline className="baseline" points={line(points)}/><polyline className="expected" points={line(expectedPoints)}/></svg><div className="chart-legend"><span><i className="solid"></i>Baseline Forecast</span><span><i className="dash"></i>Expected Forecast</span></div></div>;
}
function ForecastMetrics({ forecast }) { if (!forecast) return null; return <div className="metric-strip"><div><span>End of period</span><strong>{money(forecast.final_balance)}</strong></div><div><span>Lowest Balance</span><strong className="negative">{money(forecast.lowest_balance?.balance)}</strong><small>{dateLabel(forecast.lowest_balance?.date)}</small></div>{forecast.shortfall ? <div className="risk"><span>Cash shortfall risk</span><strong>{money(forecast.shortfall.balance)}</strong><small>{dateLabel(forecast.shortfall.date)}</small></div> : <div className="safe"><span>No forecast shortfall</span><strong>Clear</strong><small>Based on current records</small></div>}</div>; }
function CompactEvents({ rows }) { return rows?.length ? rows.slice(0, 6).map((row, index) => <div className="event-row" key={`${row.date}-${row.name}-${index}`}><time>{dateLabel(row.date).slice(0, 6)}</time><span>{row.name}<small>{row.category || row.source_type || row.source}</small></span><strong className={amountClass(row.amount)}>{money(row.amount)}</strong></div>) : <Empty title="Nothing scheduled">No matching financial events in this period.</Empty>; }
function BudgetSnippet({ rows }) { return rows?.length ? rows.slice(0, 5).map((row, i) => <div className="budget-line" key={row.category || row.name || i}><div><span>{row.category || row.name}</span><strong>{row.status?.replace('_', ' ') || row.utilisation || row.progress || 'Tracking'}</strong></div><progress value={Math.min(Number(row.utilisation_percent || row.percentage || 0), 100)} max="100"></progress></div>) : <Empty title="No budgets yet">Create budgets to see spending against targets.</Empty>; }
function GoalMini({ goal }) { const pct = Number(goal.progress?.percentage || 0); return <div className="goal-mini"><div><strong>{goal.name}</strong><small>{goal.progress?.status || goal.calculated_status}</small></div><progress value={Math.min(pct, 100)} max="100"></progress><span>{money(goal.progress?.current)} of {money(goal.progress?.target)} • {pct}%</span></div>; }

function GoalsPage({ goals, accounts, onEdit, onAdd, onComplete }) {
  const totals = goals.reduce((acc, goal) => { acc.target += parseAmount(goal.target_amount); acc.current += parseAmount(goal.progress?.current || goal.current_amount); if (goal.progress?.status === 'on_track' || goal.progress?.status === 'ahead') acc.onTrack += 1; return acc; }, { target: 0, current: 0, onTrack: 0 });
  return <section className="stack"><div className="kpi-grid four"><Kpi icon="🎯" label="Active Goals" value={goals.length}/><Kpi icon="🏁" label="Total Target" value={totals.target}/><Kpi icon="💰" label="Allocated / Saved" value={totals.current}/><Kpi icon="✅" label="Goals On Track" value={`${totals.onTrack} of ${goals.length}`}/></div><article className="panel"><PanelHead title="Financial Goals" action="+ Add Goal" onAction={onAdd}/>{goals.length ? <div className="goal-grid">{goals.map((goal) => <article className="goal-card" key={goal.id}><div className="goal-card-head"><div><h3>{goal.name}</h3><small>{goal.goal_type?.replace('_', ' ')} • {goal.priority}</small></div><Badge tone={goal.progress?.status === 'behind' ? 'warn' : 'ok'}>{goal.progress?.status || goal.calculated_status}</Badge></div><progress value={Math.min(Number(goal.progress?.percentage || 0), 100)} max="100"></progress><div className="goal-values"><span>{money(goal.progress?.current)} saved</span><strong>{goal.progress?.percentage || 0}%</strong><span>{money(goal.progress?.remaining)} left</span></div><p>{goal.progress?.explanation}</p><div className="goal-actions"><button onClick={() => onEdit(goal)}>Edit</button><button className="primary ghost" onClick={() => onComplete(goal.id)}>Complete</button></div></article>)}</div> : <Empty title="No Goals Yet">Create a goal to start planning for a holiday, emergency fund, debt target or annual expense.<button className="primary" onClick={onAdd}>+ Add Goal</button></Empty>}</article><article className="panel"><h2>Account allocation model</h2><p>Goal progress uses explicit allocations and contributions so one savings balance is not counted against multiple goals unless you allocate it that way.</p><p className="muted">Linked accounts available: {accounts.length || 0}</p></article></section>;
}

function ForecastPage({ forecast }) { return <section className="panel"><PanelHead title="Cash Flow"/><CashFlowChart baseline={forecast} expected={forecast}/><ForecastMetrics forecast={forecast}/><div className="table simple"><div className="thead"><span>Date</span><span>Item</span><span>Amount</span><span>Forecast balance</span></div>{(forecast?.events || []).map((item, i) => <div className="tr" key={i}><span>{dateLabel(item.date)}</span><span>{item.name}</span><span className={amountClass(item.amount)}>{money(item.amount)}</span><span>{money(item.forecast_balance)}</span></div>)}</div></section>; }
function CalendarPage({ command }) { return <section className="panel"><PanelHead title="Financial Calendar"/><CompactEvents rows={command?.upcoming || []}/></section>; }
function SpendingIntelligence({ suggestions, dismissSuggestion }) { return <section className="panel"><PanelHead title="Spending Intelligence"/><p className="muted">Review merchant, category, recurring and unusual-spending suggestions. Suggestions remain explainable and user-controlled.</p>{suggestions?.length ? suggestions.map((item) => <div className="suggestion" key={item.id}><div><strong>{item.title || item.suggestion_type}</strong><p>{item.explanation || item.reason || item.evidence}</p></div><Badge>{item.confidence || 'review'}</Badge><button onClick={() => dismissSuggestion(item.id)}>Dismiss</button></div>) : <Empty title="No suggestions waiting">Spending Intelligence has no unresolved items.</Empty>}</section>; }

function RecordTable({ active, data, onEdit }) {
  const cfg = { Accounts: ['accounts', data.accounts, 'Account'], Transactions: ['transactions', data.transactions, 'Transaction'], Income: ['income', data.income, 'Income'], 'Recurring Expenses': ['recurring', data.recurring, 'Recurring Expense'], Bills: ['bills', data.bills, 'Bill'], 'Planned Spending': ['planned', data.planned, 'Planned Spending'], Categories: ['categories', data.categories, 'Category'] }[active];
  const [type, rows, label] = cfg;
  return <section className={`panel ${active === 'Accounts' ? 'accounts-panel' : ''}`}><div className="panel-head"><div><h2>{active}</h2><p className="muted">Create and maintain {active.toLowerCase()} using the current Fynvo data model.</p></div><button className="primary ghost" onClick={() => onEdit({ type, label: `New ${label}`, row: { id: null }, values: normaliseRecord(type, {}) })}>+ Add</button></div>{rows.length ? <div className="table"><div className="thead"><span>Date</span><span>Name</span><span>Amount</span><span>Status</span><span></span></div>{rows.map((row) => <div className="tr" key={row.id}><span>{dateLabel(row.date || row.transaction_date || row.due_date || row.next_due_date || row.next_payment_date || row.planned_date)}</span><span>{row.name || row.description || row.merchant || row.category || row.account_type}</span><span className={amountClass(row.amount || row.estimated_amount || row.current_balance)}>{money(row.amount || row.estimated_amount || row.current_balance)}</span><span>{active === 'Accounts' ? accountTypeLabel(row.account_type) : row.status || row.completeness || row.category_type || 'Active'}</span><button onClick={() => onEdit({ type, label, row, values: normaliseRecord(type, row) })}>Edit</button></div>)}</div> : <Empty title={`No ${active.toLowerCase()} yet`}>Use Add to create the first record.</Empty>}</section>;
}

function Budgeting({ budgets, analysis, onEdit }) { return <section className="panel"><PanelHead title="Budgeting"/><div className="summary-row"><span>Base budget</span><strong>{money(analysis?.summary?.base_budget)}</strong></div><div className="summary-row"><span>Actual spending</span><strong>{money(analysis?.summary?.actual)}</strong></div><div className="summary-row"><span>Forecast spending</span><strong>{money(analysis?.summary?.forecast)}</strong></div><RecordList rows={budgets} onEdit={onEdit}/></section>; }
function RecordList({ rows, onEdit }) { return rows?.length ? rows.map((row) => <div className="list-row" key={row.id}><span>{row.name}<small>{row.period}</small></span><strong>{money(row.amount)}</strong><button onClick={() => onEdit(row)}>Edit</button></div>) : <Empty title="No records yet">Create a record to get started.</Empty>; }
function CsvImport({ state, setState, accounts, previewImport, commitImport }) { return <section className="panel"><PanelHead title="CSV Import & Reconciliation"/><form className="form-grid" onSubmit={previewImport}><Field label="Filename" value={state.filename} onChange={(e) => setState({ ...state, filename: e.target.value })}/><Field label="Account"><select value={state.account_id} onChange={(e) => setState({ ...state, account_id: e.target.value })}><option value="">Choose account</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></Field><label className="field wide"><span>CSV text</span><textarea rows="10" value={state.csv_text} onChange={(e) => setState({ ...state, csv_text: e.target.value })}/></label><button className="primary">Preview CSV</button></form>{state.preview && <div className="notice"><p>{state.preview.valid_count || 0} valid rows, {state.preview.duplicate_count || 0} duplicates.</p><button className="primary" onClick={commitImport}>Commit Import</button></div>}</section>; }
function ImportHistory({ rows }) { return <section className="panel"><PanelHead title="Import History"/>{rows?.length ? rows.map((row) => <div className="list-row" key={row.id}><span>{row.filename}<small>{dateLabel(row.created_at)}</small></span><strong>{row.imported_count} imported</strong></div>) : <Empty title="No imports yet">Import a CSV to see history.</Empty>}</section>; }
function ReviewQueue({ rows, acceptMatch }) { return <section className="panel"><PanelHead title="Reconciliation Review Queue"/>{rows?.length ? rows.map((row) => <div className="suggestion" key={row.id}><div><strong>{row.transaction?.description || row.source_type}</strong><p>{row.status} • confidence {row.confidence}</p></div><button className="primary ghost" onClick={() => acceptMatch(row.id)}>Accept</button></div>) : <Empty title="No reconciliation items">Imported transactions that need review will appear here.</Empty>}</section>; }

function EditModal({ edit, setEdit, onSubmit, data }) {
  const values = edit.values || {};
  const set = (key, value) => setEdit({ ...edit, values: { ...values, [key]: value } });
  return <div className="modal-backdrop" role="presentation"><form className="modal" onSubmit={onSubmit}><div className="panel-head"><h2>{edit.label}</h2><button type="button" aria-label={`Close ${edit.label}`} onClick={() => setEdit(null)}>×</button></div><DynamicFields type={edit.type} values={values} set={set} data={data}/><div className="modal-actions"><button type="button" onClick={() => setEdit(null)}>Cancel</button><button className="primary">Save</button></div></form></div>;
}
function DynamicFields({ type, values, set, data }) {
  const accountSelect = (key) => <select value={values[key] || ''} onChange={(e) => set(key, e.target.value)}><option value="">Choose account</option>{data.accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>;
  const text = (key, label, inputType = 'text', required = false) => <Field label={label}><input type={inputType} required={required} value={values[key] ?? ''} onChange={(e) => set(key, e.target.value)}/></Field>;
  if (type === 'transactions') return <div className="form-grid">{text('date', 'Date', 'date', true)}{text('amount', 'Amount', 'text', true)}{text('description', 'Description', 'text', true)}<Field label="Account">{accountSelect('account_id')}</Field><Field label="Type"><select value={values.transaction_type} onChange={(e) => set('transaction_type', e.target.value)}><option value="expense">Expense</option><option value="income">Income</option></select></Field>{text('merchant', 'Merchant')}{text('category', 'Category')}{text('notes', 'Notes')}</div>;
  if (type === 'income') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('amount', 'Amount')}{text('next_payment_date', 'Next payment', 'date')}<Field label="Frequency"><select value={values.frequency} onChange={(e) => set('frequency', e.target.value)}><option>weekly</option><option>fortnightly</option><option>monthly</option><option>quarterly</option><option>annual</option></select></Field><Field label="Destination account">{accountSelect('destination_account_id')}</Field>{text('payer', 'Payer')}{text('category', 'Category')}{text('notes', 'Notes')}</div>;
  if (type === 'recurring') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('amount', 'Amount')}{text('next_due_date', 'Next due', 'date')}<Field label="Frequency"><select value={values.frequency} onChange={(e) => set('frequency', e.target.value)}><option>weekly</option><option>fortnightly</option><option>monthly</option><option>quarterly</option><option>annual</option></select></Field><Field label="Account">{accountSelect('account_id')}</Field>{text('category', 'Category')}{text('expense_type', 'Expense type')}{text('notes', 'Notes')}</div>;
  if (type === 'bills') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('amount', 'Amount')}{text('due_date', 'Due date', 'date')}{text('provider', 'Provider')}{text('bill_type', 'Bill type')}<Field label="Priority"><select value={values.priority} onChange={(e) => set('priority', e.target.value)}><option>low</option><option>normal</option><option>high</option></select></Field><Field label="Account">{accountSelect('account_id')}</Field>{text('notes', 'Notes')}</div>;
  if (type === 'planned') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('estimated_amount', 'Estimated amount')}{text('planned_date', 'Planned date', 'date')}{text('category', 'Category')}{text('merchant', 'Merchant')}<Field label="Status"><select value={values.status} onChange={(e) => set('status', e.target.value)}><option>wishlist</option><option>planned</option><option>committed</option><option>purchased</option><option>cancelled</option></select></Field>{text('description', 'Description')}{text('notes', 'Notes')}</div>;
  if (type === 'goals') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('target_amount', 'Target amount')}{text('current_amount', 'Current amount')}{text('target_date', 'Target date', 'date')}<Field label="Goal type"><select value={values.goal_type} onChange={(e) => set('goal_type', e.target.value)}><option value="savings">Savings</option><option value="target_balance">Target balance</option><option value="planned_purchase">Planned purchase</option><option value="annual">Recurring / annual</option><option value="debt_reduction">Debt reduction</option></select></Field><Field label="Priority"><select value={values.priority} onChange={(e) => set('priority', e.target.value)}><option>high</option><option>medium</option><option>low</option></select></Field><Field label="Contribution frequency"><select value={values.contribution_frequency} onChange={(e) => set('contribution_frequency', e.target.value)}><option>weekly</option><option>fortnightly</option><option>monthly</option></select></Field>{text('contribution_amount', 'Current contribution')}{text('description', 'Description')}{text('notes', 'Notes')}</div>;
  if (type === 'accounts') return <div className="form-grid account-form">{text('name', 'Account name', 'text', true)}{text('opening_balance', 'Opening balance', 'text', true)}<Field label="Account type"><select required value={values.account_type} onChange={(e) => set('account_type', e.target.value)}>{accountTypeOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>{text('institution', 'Institution')}{text('description', 'Description')}<p className="field-hint wide">Enter liability opening balances as a positive amount owing. Fynvo applies the liability sign semantics internally.</p></div>;
  if (type === 'categories') return <div className="form-grid">{text('name', 'Name', 'text', true)}<Field label="Type"><select value={values.category_type} onChange={(e) => set('category_type', e.target.value)}><option>expense</option><option>income</option><option>transfer</option></select></Field>{text('icon', 'Icon')}{text('color', 'Colour')}{text('notes', 'Notes')}</div>;
  if (type === 'budgets') return <div className="form-grid">{text('name', 'Name', 'text', true)}{text('amount', 'Amount')}{text('start_date', 'Start date', 'date')}<Field label="Period"><select value={values.period} onChange={(e) => set('period', e.target.value)}><option>weekly</option><option>fortnightly</option><option>monthly</option><option>quarterly</option><option>annual</option></select></Field>{text('category_name', 'Category')}{text('notes', 'Notes')}</div>;
  return <div className="form-grid">{Object.keys(values).map((key) => text(key, key))}</div>;
}
