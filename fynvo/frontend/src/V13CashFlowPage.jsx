import { useEffect, useMemo, useState } from 'react';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

const money = (value) => new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value || 0));
const compactMoney = (value) => {
  const number = Number(value || 0);
  const absolute = Math.abs(number);
  if (absolute >= 10000) return `${number < 0 ? '-' : ''}$${Math.round(absolute / 1000)}k`;
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(number);
};
const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`)) : '';
const horizons = [
  ['7d', '7 days'], ['14d', '14 days'], ['30d', '30 days'], ['60d', '60 days'], ['90d', '90 days'], ['6m', '6 months'], ['12m', '12 months'],
];

function niceStep(span) {
  const rough = Math.max(span / 4, 1);
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return factor * magnitude;
}

function ForecastChart({ points = [] }) {
  const values = points.map((point) => Number(point.balance || 0));
  if (points.length < 2) return <div className="v13-empty">Not enough forecast data to draw a projection yet.</div>;

  const rawMin = Math.min(...values, 0);
  const rawMax = Math.max(...values, 0);
  const step = niceStep(Math.max(rawMax - rawMin, 1));
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step || step;
  const span = Math.max(max - min, step);
  const width = 900;
  const height = 300;
  const left = 92;
  const right = 18;
  const top = 18;
  const bottom = 46;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const path = points.map((point, index) => {
    const x = left + (index / Math.max(points.length - 1, 1)) * plotWidth;
    const y = top + plotHeight - ((Number(point.balance || 0) - min) / span) * plotHeight;
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');

  const yTicks = Array.from({ length: 5 }, (_, index) => max - (span * index / 4));
  const targetXTicks = points.length <= 8 ? points.length : 5;
  const xIndexes = [...new Set(Array.from({ length: targetXTicks }, (_, index) => Math.round(index * (points.length - 1) / Math.max(targetXTicks - 1, 1))))];

  return <div className="v13-chart-wrap">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Projected household balance over time with readable currency and date axes">
      {yTicks.map((tick, index) => {
        const y = top + index * plotHeight / 4;
        return <g key={`y-${index}`}><line className="v14-chart-grid" x1={left} y1={y} x2={width - right} y2={y}/><text className="v14-chart-axis-label" x={left - 14} y={y + 5} textAnchor="end">{compactMoney(tick)}</text></g>;
      })}
      {xIndexes.map((pointIndex) => {
        const x = left + (pointIndex / Math.max(points.length - 1, 1)) * plotWidth;
        return <g key={`x-${pointIndex}`}><line className="v14-chart-grid vertical" x1={x} y1={top} x2={x} y2={top + plotHeight}/><text className="v14-chart-axis-label" x={x} y={height - 14} textAnchor={pointIndex === 0 ? 'start' : pointIndex === points.length - 1 ? 'end' : 'middle'}>{dateLabel(points[pointIndex]?.date)}</text></g>;
      })}
      <path className="v14-chart-line" d={path}/>
      {points.map((point, index) => {
        const x = left + (index / Math.max(points.length - 1, 1)) * plotWidth;
        const y = top + plotHeight - ((Number(point.balance || 0) - min) / span) * plotHeight;
        return <circle key={`${point.date}-${index}`} className="v14-chart-point" cx={x} cy={y} r="5"><title>{dateLabel(point.date)}: {money(point.balance)}</title></circle>;
      })}
    </svg>
    <div className="v14-chart-summary" aria-hidden="true"><span>Low {compactMoney(Math.min(...values))}</span><span>High {compactMoney(Math.max(...values))}</span></div>
  </div>;
}

export default function V13CashFlowPage({ onClose }) {
  const [tab, setTab] = useState('Cash Flow');
  const [horizon, setHorizon] = useState('30d');
  const [projection, setProjection] = useState(null);
  const [upcoming, setUpcoming] = useState(null);
  const [calendar, setCalendar] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [purchase, setPurchase] = useState({ amount: '', proposed_date: '', account_id: '', description: '' });
  const [simulation, setSimulation] = useState(null);
  const [bufferEdit, setBufferEdit] = useState({ account_id: '', minimum_balance: '' });

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [cash, future, days, accountRows] = await Promise.all([
        api(`/v1.3/cash-flow?horizon=${horizon}&mode=expected`).then((r) => r.json()),
        api(`/v1.3/upcoming?horizon=${horizon}`).then((r) => r.json()),
        api('/v1.3/calendar?days=31').then((r) => r.json()),
        api('/accounts').then((r) => r.json()),
      ]);
      setProjection(cash);
      setUpcoming(future);
      setCalendar(days);
      setAccounts(Array.isArray(accountRows) ? accountRows : []);
    } catch {
      setError('Could not load the cash-flow view.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [horizon]);

  const accountNames = useMemo(() => Object.fromEntries(accounts.map((row) => [String(row.id), row.name])), [accounts]);

  async function saveBuffer(event) {
    event.preventDefault();
    if (!bufferEdit.account_id) return;
    await api(`/v1.3/accounts/${bufferEdit.account_id}/buffer`, { method: 'PUT', body: JSON.stringify({ minimum_balance: bufferEdit.minimum_balance || null }) });
    setBufferEdit({ account_id: '', minimum_balance: '' });
    await load();
  }

  async function simulate(event) {
    event.preventDefault();
    const response = await api('/v1.3/purchase-simulator', { method: 'POST', body: JSON.stringify({ ...purchase, account_id: Number(purchase.account_id), horizon }) });
    setSimulation(response.ok ? await response.json() : null);
  }

  return <main className="v13-shell"><header className="v13-head"><div><span className="v13-kicker">Fynvo v1.4.0</span><h1>Cash Flow Intelligence</h1><p>See what is coming in, what is going out, and where the household balance is heading.</p></div><button type="button" onClick={onClose}>Back to Fynvo</button></header>
    <div className="v13-tabs" role="tablist">{['Cash Flow', 'Calendar', 'Upcoming'].map((name) => <button key={name} type="button" className={tab === name ? 'active' : ''} onClick={() => setTab(name)}>{name}</button>)}</div>
    {error && <p className="error">{error}</p>}
    {loading ? <section className="panel"><p>Loading forecast…</p></section> : tab === 'Cash Flow' ? <>
      <section className="v13-toolbar panel"><label>Forecast period<select value={horizon} onChange={(event) => setHorizon(event.target.value)}>{horizons.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div><span>Forecast status</span><strong>Projected, not confirmed</strong></div></section>
      <section className="v13-summary">{[
        ['Opening balance', projection?.starting_balance], ['Expected income', projection?.income_total], ['Expected expenses', projection?.expense_total], ['Projected balance', projection?.final_balance], ['Lowest balance', projection?.lowest_balance?.balance],
      ].map(([label, value]) => <article className="panel" key={label}><span>{label}</span><strong>{money(value)}</strong>{label === 'Lowest balance' && projection?.lowest_balance?.date && <small>{dateLabel(projection.lowest_balance.date)}</small>}</article>)}</section>
      <section className="panel"><div className="panel-head"><div><h2>Projected balance</h2><p className="muted">Actual opening position followed by expected future movement.</p></div></div><ForecastChart points={projection?.chart_points || []}/></section>
      {!!projection?.warnings?.length && <section className="panel"><div className="panel-head"><div><h2>Balance warnings</h2><p className="muted">Warnings show the first point where an account crosses its safety threshold.</p></div></div><div className="v13-warning-list">{projection.warnings.map((warning, index) => <article key={`${warning.kind}-${warning.account_id}-${index}`} className={`v13-warning ${warning.kind}`}><strong>{warning.kind === 'negative_balance' ? 'Potential cash shortfall' : 'Low balance predicted'}</strong><span>{warning.account_name} · {dateLabel(warning.date)}</span><p>Projected balance {money(warning.projected_balance)}. Cause: {warning.cause}.</p>{warning.shortfall && <small>Below buffer by {money(warning.shortfall)}</small>}{warning.required_to_avoid && <small>{money(warning.required_to_avoid)} required to avoid a negative balance.</small>}</article>)}</div></section>}
      <section className="v13-two-col"><section className="panel"><div className="panel-head"><div><h2>Account safety buffers</h2><p className="muted">Set a minimum balance that Fynvo should warn about.</p></div></div><form className="v13-form" onSubmit={saveBuffer}><label>Account<select value={bufferEdit.account_id} onChange={(event) => setBufferEdit({ ...bufferEdit, account_id: event.target.value })}><option value="">Choose account</option>{accounts.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label>Minimum balance<input inputMode="decimal" value={bufferEdit.minimum_balance} onChange={(event) => setBufferEdit({ ...bufferEdit, minimum_balance: event.target.value })} placeholder="500.00"/></label><button className="primary" type="submit">Save buffer</button></form></section>
      <section className="panel"><div className="panel-head"><div><h2>Can I afford this?</h2><p className="muted">Run an isolated purchase scenario without changing real records.</p></div></div><form className="v13-form" onSubmit={simulate}><label>Amount<input required inputMode="decimal" value={purchase.amount} onChange={(event) => setPurchase({ ...purchase, amount: event.target.value })}/></label><label>Proposed date<input required type="date" value={purchase.proposed_date} onChange={(event) => setPurchase({ ...purchase, proposed_date: event.target.value })}/></label><label>Account<select required value={purchase.account_id} onChange={(event) => setPurchase({ ...purchase, account_id: event.target.value })}><option value="">Choose account</option>{accounts.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label>Description<input value={purchase.description} onChange={(event) => setPurchase({ ...purchase, description: event.target.value })}/></label><button className="primary" type="submit">Simulate purchase</button></form>{simulation && <div className="v13-simulation"><span>Balance before <strong>{money(simulation.balance_before)}</strong></span><span>After purchase <strong>{money(simulation.projected_balance_after)}</strong></span><span>Lowest afterwards <strong>{money(simulation.lowest_projected_balance_afterwards)}</strong></span><span>{simulation.negative_balance_predicted ? 'Negative balance predicted' : simulation.buffer_breached ? 'Safety buffer breached' : 'No shortfall predicted in this horizon'}</span></div>}</section></section>
      <section className="panel"><div className="panel-head"><div><h2>Forecast breakdown</h2><p className="muted">Select any row to understand what changes the projected balance.</p></div></div><div className="table v13-events"><div className="thead"><span>Date</span><span>Item</span><span>Type</span><span>Amount</span><span>Projected</span></div>{(projection?.events || []).slice(0, 80).map((row, index) => <div className="tr" key={`${row.source_type}-${row.source_id}-${row.date}-${index}`}><span>{dateLabel(row.date)}</span><span>{row.name}<small>{row.explanation}</small></span><span>{row.direction}</span><strong>{row.direction === 'transfer' ? '$0.00 net' : money(row.amount)}</strong><span>{money(row.forecast_balance)}</span></div>)}</div></section>
    </> : tab === 'Calendar' ? <section className="panel"><div className="panel-head"><div><h2>Financial Calendar</h2><p className="muted">Daily income, expenses and net movement for the next month.</p></div></div>{calendar?.days?.length ? <div className="v13-calendar-grid">{calendar.days.map((day) => <article key={day.date}><strong>{dateLabel(day.date)}</strong><span>Income {money(day.income)}</span><span>Expenses {money(day.expenses)}</span><span>Net {money(day.net)}</span><small>{day.items.length} item{day.items.length === 1 ? '' : 's'}</small></article>)}</div> : <div className="v13-empty">No scheduled financial events in this period.</div>}</section> : <section className="panel"><div className="panel-head"><div><h2>Upcoming money</h2><p className="muted">Overdue items remain visible until they are resolved.</p></div></div><div className="v13-upcoming">{(upcoming?.groups || []).map((group) => <section key={group.name}><h3>{group.name}</h3>{group.items.length ? group.items.map((item, index) => <div className="list-row" key={`${item.source_type}-${item.source_id}-${index}`}><span>{item.name}<small>{item.direction} · {dateLabel(item.date)}{item.account_id ? ` · ${accountNames[String(item.account_id)] || 'Account'}` : ''}</small></span><strong>{item.direction === 'transfer' ? '$0.00 net' : money(item.amount)}</strong></div>) : <p className="muted">Nothing here.</p>}</section>)}</div></section>}
  </main>;
}
