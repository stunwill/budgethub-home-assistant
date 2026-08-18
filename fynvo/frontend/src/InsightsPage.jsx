import { useEffect, useMemo, useState } from 'react';
import './insights-v14.css';

const importanceLabels = {
  warning: 'Warning',
  attention: 'Needs attention',
  opportunity: 'Positive signal',
  information: 'Information',
};

const categoryLabels = {
  cash_flow: 'Cash Flow',
  budgets: 'Budgets',
  spending: 'Spending',
  recurring_costs: 'Recurring Costs',
  income: 'Income',
  savings: 'Savings',
  goals: 'Goals',
  scenarios: 'Scenarios',
  data_quality: 'Data Quality',
};

const statusLabel = (value) => String(value || 'stable').replaceAll('_', ' ');
const api = (path) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } });

function EvidenceValue({ value }) {
  if (Array.isArray(value)) {
    return value.length ? <ul className="insight-evidence-list">{value.slice(0, 10).map((item, index) => <li key={index}>{typeof item === 'object' ? Object.entries(item).filter(([, nested]) => nested !== null && nested !== undefined && typeof nested !== 'object').map(([key, nested]) => `${key.replaceAll('_', ' ')}: ${nested}`).join(' · ') : String(item)}</li>)}</ul> : <span>None</span>;
  }
  if (value && typeof value === 'object') {
    return <dl className="insight-evidence-nested">{Object.entries(value).filter(([, nested]) => nested !== null && nested !== undefined && typeof nested !== 'object').map(([key, nested]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(nested)}</dd></div>)}</dl>;
  }
  return <span>{String(value)}</span>;
}

function Evidence({ evidence, supportingRefs }) {
  const entries = Object.entries(evidence || {}).filter(([, value]) => value !== null && value !== undefined);
  if (!entries.length && !supportingRefs?.length) return null;
  return <details className="insight-evidence"><summary>Why Fynvo is showing this</summary>
    {entries.length ? <dl>{entries.map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd><EvidenceValue value={value}/></dd></div>)}</dl> : null}
    {supportingRefs?.length ? <div className="insight-supporting"><strong>Supporting records</strong><EvidenceValue value={supportingRefs}/></div> : null}
  </details>;
}

function InsightCard({ insight, onDismiss, onReviewed, onNavigate, history = false }) {
  return <article className={`insight-card insight-${insight.importance}`} aria-label={`${importanceLabels[insight.importance] || insight.importance}: ${insight.title}`}>
    <div className="insight-card-head"><div><span className="insight-category">{categoryLabels[insight.category] || insight.category}</span><h3>{insight.title}</h3></div><span className={`insight-pill ${insight.importance}`}>{importanceLabels[insight.importance] || insight.importance}</span></div>
    <p>{insight.summary}</p>
    <div className="insight-meta"><span>Status: <strong>{statusLabel(insight.status)}</strong></span>{insight.confidence && <span>Confidence: <strong>{insight.confidence}</strong></span>}{insight.updated_at && <span>Updated: <strong>{new Date(insight.updated_at).toLocaleString('en-AU')}</strong></span>}</div>
    <Evidence evidence={insight.evidence} supportingRefs={insight.supporting_refs}/>
    <div className="insight-actions">
      {insight.action_target && <button className="primary ghost" onClick={() => onNavigate(insight.action_target)}>{insight.action_label || 'View details'} →</button>}
      {!history && insight.status === 'new' && <button onClick={() => onReviewed(insight.id)}>Mark reviewed</button>}
      {!history && insight.status !== 'dismissed' && <button onClick={() => onDismiss(insight.id)}>Dismiss</button>}
    </div>
  </article>;
}

export default function InsightsPage({ insights = [], health, onDismiss, onReviewed, onNavigate, onRefresh }) {
  const [importance, setImportance] = useState('all');
  const [category, setCategory] = useState('all');
  const [period, setPeriod] = useState('current');
  const [historyRows, setHistoryRows] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const dimensions = Object.values(health?.dimensions || {});

  useEffect(() => {
    if (period === 'current' || historyRows.length || historyLoading) return;
    let cancelled = false;
    setHistoryLoading(true);
    api('/insights?status=all&refresh=false').then(async (response) => response.ok ? response.json() : []).then((rows) => { if (!cancelled) setHistoryRows(Array.isArray(rows) ? rows : []); }).finally(() => { if (!cancelled) setHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [period, historyRows.length, historyLoading]);

  const source = period === 'current' ? insights : historyRows;
  const visible = useMemo(() => {
    const now = Date.now();
    const ageLimit = period === '30d' ? 30 : period === '90d' ? 90 : null;
    return source.filter((item) => {
      if (importance !== 'all' && item.importance !== importance) return false;
      if (category !== 'all' && item.category !== category) return false;
      if (period === 'history' && !['dismissed', 'resolved'].includes(item.status)) return false;
      if (ageLimit) {
        const updated = item.updated_at ? new Date(item.updated_at).getTime() : 0;
        if (!updated || now - updated > ageLimit * 86400000) return false;
      }
      return true;
    });
  }, [source, importance, category, period]);

  async function refreshAll() {
    setHistoryRows([]);
    await onRefresh();
  }

  return <section className="insights-page stack">
    <section className="insight-summary-grid" aria-label="Financial Health summary">
      <article className="panel health-headline"><span>Financial Health</span><h2>{health?.headline || 'Financial health is being calculated'}</h2><p>Fynvo reports transparent component statuses rather than an unexplained overall score.</p></article>
      <article className="panel insight-count"><strong>{health?.warning_count || 0}</strong><span>Warnings</span></article>
      <article className="panel insight-count"><strong>{health?.attention_count || 0}</strong><span>Need attention</span></article>
      <article className="panel insight-count"><strong>{health?.opportunity_count || 0}</strong><span>Positive signals</span></article>
    </section>

    <article className="panel">
      <div className="panel-head"><div><h2>Financial Health overview</h2><p className="muted">Each status is derived from Fynvo's existing Cash Flow, Budget, Goal and transaction calculations.</p></div><button className="primary ghost" onClick={refreshAll}>Refresh insights</button></div>
      <div className="health-dimensions">{dimensions.map((item) => <div className="health-dimension" key={item.label}><span>{item.label}</span><strong>{statusLabel(item.status)}</strong></div>)}</div>
      <div className="health-context"><span>Budgets on track: <strong>{health?.budgets_on_track?.count || 0} of {health?.budgets_on_track?.total || 0}</strong></span><span>Goals on track: <strong>{health?.goals_on_track?.count || 0} of {health?.goals_on_track?.total || 0}</strong></span></div>
    </article>

    <article className="panel">
      <div className="panel-head insights-toolbar"><div><h2>{period === 'current' ? 'Current Insights' : 'Insight history'}</h2><p className="muted">Signals are factual, explainable and based on your Fynvo data. Date views use the Insight generation/update date and do not truncate a forward-looking forecast period.</p></div><div className="insight-filters"><label>View<select value={period} onChange={(event) => setPeriod(event.target.value)}><option value="current">Current</option><option value="30d">Last 30 days</option><option value="90d">Last 90 days</option><option value="history">Historical / resolved</option></select></label><label>Importance<select value={importance} onChange={(event) => setImportance(event.target.value)}><option value="all">All</option><option value="warning">Warning</option><option value="attention">Attention</option><option value="opportunity">Positive</option><option value="information">Information</option></select></label><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All</option>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div></div>
      {historyLoading && period !== 'current' ? <div className="insight-empty" role="status"><strong>Loading Insight history…</strong></div> : visible.length ? <div className="insight-list">{visible.map((item) => <InsightCard key={item.id} insight={item} history={period === 'history'} onDismiss={onDismiss} onReviewed={onReviewed} onNavigate={onNavigate}/>)}</div> : <div className="insight-empty"><strong>No matching Insights</strong><p>Fynvo will surface a signal when the underlying financial data supports one.</p></div>}
    </article>
  </section>;
}
