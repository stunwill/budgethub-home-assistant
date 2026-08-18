import { useMemo, useState } from 'react';
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

function Evidence({ evidence }) {
  const entries = Object.entries(evidence || {}).filter(([, value]) => value !== null && value !== undefined && !Array.isArray(value) && typeof value !== 'object');
  if (!entries.length) return null;
  return <details className="insight-evidence"><summary>Why Fynvo is showing this</summary><dl>{entries.map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl></details>;
}

function InsightCard({ insight, onDismiss, onReviewed, onNavigate }) {
  return <article className={`insight-card insight-${insight.importance}`}>
    <div className="insight-card-head"><div><span className="insight-category">{categoryLabels[insight.category] || insight.category}</span><h3>{insight.title}</h3></div><span className={`insight-pill ${insight.importance}`}>{importanceLabels[insight.importance] || insight.importance}</span></div>
    <p>{insight.summary}</p>
    {insight.confidence && <p className="insight-confidence"><strong>Confidence:</strong> {insight.confidence}</p>}
    <Evidence evidence={insight.evidence}/>
    <div className="insight-actions">
      {insight.action_target && <button className="primary ghost" onClick={() => onNavigate(insight.action_target)}>{insight.action_label || 'View details'} →</button>}
      {insight.status === 'new' && <button onClick={() => onReviewed(insight.id)}>Mark reviewed</button>}
      <button onClick={() => onDismiss(insight.id)}>Dismiss</button>
    </div>
  </article>;
}

export default function InsightsPage({ insights = [], health, onDismiss, onReviewed, onNavigate, onRefresh }) {
  const [importance, setImportance] = useState('all');
  const [category, setCategory] = useState('all');
  const visible = useMemo(() => insights.filter((item) => (importance === 'all' || item.importance === importance) && (category === 'all' || item.category === category)), [insights, importance, category]);
  const dimensions = Object.values(health?.dimensions || {});

  return <section className="insights-page stack">
    <section className="insight-summary-grid">
      <article className="panel health-headline"><span>Financial Health</span><h2>{health?.headline || 'Financial health is being calculated'}</h2><p>Fynvo reports transparent component statuses rather than an unexplained overall score.</p></article>
      <article className="panel insight-count"><strong>{health?.warning_count || 0}</strong><span>Warnings</span></article>
      <article className="panel insight-count"><strong>{health?.attention_count || 0}</strong><span>Need attention</span></article>
      <article className="panel insight-count"><strong>{health?.opportunity_count || 0}</strong><span>Positive signals</span></article>
    </section>

    <article className="panel">
      <div className="panel-head"><div><h2>Financial Health overview</h2><p className="muted">Each status is derived from Fynvo's existing Cash Flow, Budget, Goal and transaction calculations.</p></div><button className="primary ghost" onClick={onRefresh}>Refresh insights</button></div>
      <div className="health-dimensions">{dimensions.map((item) => <div className="health-dimension" key={item.label}><span>{item.label}</span><strong>{statusLabel(item.status)}</strong></div>)}</div>
      <div className="health-context"><span>Budgets on track: <strong>{health?.budgets_on_track?.count || 0} of {health?.budgets_on_track?.total || 0}</strong></span><span>Goals on track: <strong>{health?.goals_on_track?.count || 0} of {health?.goals_on_track?.total || 0}</strong></span></div>
    </article>

    <article className="panel">
      <div className="panel-head"><div><h2>Current Insights</h2><p className="muted">Signals are factual, explainable and based on your Fynvo data.</p></div><div className="insight-filters"><label>Importance<select value={importance} onChange={(event) => setImportance(event.target.value)}><option value="all">All</option><option value="warning">Warning</option><option value="attention">Attention</option><option value="opportunity">Positive</option><option value="information">Information</option></select></label><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All</option>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div></div>
      {visible.length ? <div className="insight-list">{visible.map((item) => <InsightCard key={item.id} insight={item} onDismiss={onDismiss} onReviewed={onReviewed} onNavigate={onNavigate}/>)}</div> : <div className="insight-empty"><strong>No matching active Insights</strong><p>Fynvo will surface a signal when the underlying financial data supports one.</p></div>}
    </article>
  </section>;
}
