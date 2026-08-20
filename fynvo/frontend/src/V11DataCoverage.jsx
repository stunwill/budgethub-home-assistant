import { useEffect, useMemo, useState } from 'react';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function daysInMonth(year, monthIndex) {
  return new Date(year, monthIndex + 1, 0).getDate();
}

function segmentForMonth(range, year, monthIndex) {
  const startText = range.coverage_start || range.transaction_span_start;
  const endText = range.coverage_end || range.transaction_span_end;
  if (!startText || !endText) return null;
  const start = new Date(`${startText}T00:00:00`);
  const end = new Date(`${endText}T00:00:00`);
  const monthStart = new Date(year, monthIndex, 1);
  const monthEnd = new Date(year, monthIndex, daysInMonth(year, monthIndex));
  if (end < monthStart || start > monthEnd) return null;
  const clippedStart = start > monthStart ? start : monthStart;
  const clippedEnd = end < monthEnd ? end : monthEnd;
  const count = daysInMonth(year, monthIndex);
  const left = ((clippedStart.getDate() - 1) / count) * 100;
  const width = ((clippedEnd.getDate() - clippedStart.getDate() + 1) / count) * 100;
  return { left, width };
}

function CoverageTooltip({ range, accountName, onView }) {
  const status = range.coverage_status === 'confirmed' ? 'Confirmed coverage' : range.coverage_status === 'partial' ? 'Partial / uncertain' : 'Unknown coverage';
  return <div className="coverage-tooltip-v11">
    <strong>{accountName}</strong>
    <span>{range.filename}</span>
    <small>{range.source_type || 'csv'} · {status}</small>
    <small>Transaction span: {range.transaction_span_start || 'Unknown'} to {range.transaction_span_end || 'Unknown'}</small>
    {range.coverage_start && <small>Coverage: {range.coverage_start} to {range.coverage_end}</small>}
    <small>{range.imported_count || 0} transactions · Imported {String(range.created_at || '').replace('T', ' ').slice(0, 19)}</small>
    <button type="button" onClick={(event) => { event.stopPropagation(); onView(range.batch_id); }}>View Import</button>
  </div>;
}

function AccountTimeline({ row, year, onViewImport }) {
  const [focused, setFocused] = useState(null);
  const sourceRanges = row.source_ranges || [];
  return <div className="coverage-account-row-v11">
    <div className="coverage-account-label-v11">
      <strong>{row.account.name}</strong>
      <small>{row.quality?.status?.replaceAll('_', ' ') || 'no data'}</small>
    </div>
    <div className="coverage-month-grid-v11" role="grid" aria-label={`${row.account.name} financial data coverage for ${year}`}>
      {months.map((month, monthIndex) => <div className="coverage-month-v11" key={month} role="gridcell">
        <div className="coverage-month-name-v11">{month}</div>
        <div className="coverage-month-track-v11" aria-hidden="true"></div>
        {sourceRanges.map((range) => {
          const segment = segmentForMonth(range, year, monthIndex);
          if (!segment) return null;
          const status = range.coverage_status || 'unknown';
          const active = focused === `${range.batch_id}-${monthIndex}`;
          return <button
            type="button"
            key={`${range.batch_id}-${monthIndex}`}
            className={`coverage-segment-v11 is-${status}`}
            style={{ left: `${segment.left}%`, width: `${segment.width}%` }}
            aria-label={`${range.filename}. ${status} data coverage. ${range.transaction_span_start || ''} to ${range.transaction_span_end || ''}.`}
            onFocus={() => setFocused(`${range.batch_id}-${monthIndex}`)}
            onBlur={() => setFocused(null)}
            onMouseEnter={() => setFocused(`${range.batch_id}-${monthIndex}`)}
            onMouseLeave={() => setFocused(null)}
            onClick={() => setFocused(active ? null : `${range.batch_id}-${monthIndex}`)}
          >
            {active && <CoverageTooltip range={range} accountName={row.account.name} onView={onViewImport}/>} 
          </button>;
        })}
      </div>)}
    </div>
  </div>;
}

function ImportDetail({ batchId, onClose, onSaved }) {
  const [detail, setDetail] = useState(null);
  const [form, setForm] = useState({ coverage_status: 'unknown', coverage_start: '', coverage_end: '', coverage_note: '' });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api(`/v11/imports/${batchId}`).then(async (response) => {
      const payload = response.ok ? await response.json() : null;
      if (cancelled || !payload) return;
      setDetail(payload);
      setForm({
        coverage_status: payload.coverage_status || 'unknown',
        coverage_start: payload.coverage_start || payload.transaction_span_start || '',
        coverage_end: payload.coverage_end || payload.transaction_span_end || '',
        coverage_note: payload.coverage_note || '',
      });
    });
    return () => { cancelled = true; };
  }, [batchId]);
  const saveCoverage = async () => {
    setSaving(true);
    const response = await api(`/v11/imports/${batchId}/coverage`, { method: 'PUT', body: JSON.stringify(form) });
    setSaving(false);
    if (response.ok) {
      await onSaved();
      onClose();
    }
  };
  if (!detail) return <div className="modal-backdrop"><section className="modal"><p>Loading import…</p></section></div>;
  return <div className="modal-backdrop" role="presentation"><section className="modal detail-modal import-detail-v11" role="dialog" aria-modal="true" aria-label={`Import ${detail.filename}`}>
    <div className="panel-head"><div><h2>{detail.filename}</h2><p className="muted">Import #{detail.id}</p></div><button type="button" onClick={onClose}>×</button></div>
    <div className="detail-grid">
      <div className="detail-item"><span>Transaction span</span><strong>{detail.transaction_span_start || 'None'} → {detail.transaction_span_end || 'None'}</strong></div>
      <div className="detail-item"><span>Imported</span><strong>{detail.imported_count}</strong></div>
      <div className="detail-item"><span>Duplicates skipped</span><strong>{detail.duplicate_count}</strong></div>
      <div className="detail-item"><span>Rejected</span><strong>{detail.failed_count}</strong></div>
      <div className="detail-item"><span>Total credits</span><strong>${detail.totals?.credits}</strong></div>
      <div className="detail-item"><span>Total debits</span><strong>${detail.totals?.debits}</strong></div>
      <div className="detail-item"><span>Net movement</span><strong>${detail.totals?.net_movement}</strong></div>
    </div>
    <h3>Source coverage</h3>
    <p className="muted">The transaction span is derived from accepted rows. Confirm coverage only when the file represents all Account activity for the selected period.</p>
    <div className="form-grid">
      <label className="field"><span>Coverage status</span><select value={form.coverage_status} onChange={(event) => setForm({ ...form, coverage_status: event.target.value })}><option value="unknown">Unsure / Unknown</option><option value="partial">Partial / Incomplete</option><option value="confirmed">Complete coverage</option></select></label>
      <label className="field"><span>Coverage start</span><input type="date" value={form.coverage_start} onChange={(event) => setForm({ ...form, coverage_start: event.target.value })}/></label>
      <label className="field"><span>Coverage end</span><input type="date" value={form.coverage_end} onChange={(event) => setForm({ ...form, coverage_end: event.target.value })}/></label>
      <label className="field"><span>Coverage note</span><input value={form.coverage_note} onChange={(event) => setForm({ ...form, coverage_note: event.target.value })}/></label>
    </div>
    <h3>Imported transactions</h3>
    <div className="table import-transactions-v11"><div className="thead"><span>Date</span><span>Description</span><span>Category</span><span>Amount</span></div>{detail.transactions.map((row) => <div className="tr" key={row.id}><span>{row.transaction_date}</span><span>{row.description}<small>{row.merchant || ''}</small></span><span>{row.category || 'Uncategorised'}</span><span>${row.amount}</span></div>)}</div>
    <div className="modal-actions"><button type="button" onClick={onClose}>Close</button><button className="primary" type="button" disabled={saving} onClick={saveCoverage}>{saving ? 'Saving…' : 'Save Coverage'}</button></div>
  </section></div>;
}

export default function DataCoveragePageV11({ accounts = [] }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [coverage, setCoverage] = useState(null);
  const [selectedImport, setSelectedImport] = useState(null);
  const load = async () => {
    const response = await api(`/v11/coverage?year=${year}`);
    setCoverage(response.ok ? await response.json() : { year, accounts: [] });
  };
  useEffect(() => { load(); }, [year]);
  const rows = useMemo(() => coverage?.accounts || [], [coverage]);
  return <section className="panel data-coverage-v11">
    <div className="panel-head"><div><h2>Financial Data Coverage</h2><p className="muted">See where Fynvo has confirmed Actual source data and where history is unknown or incomplete.</p></div><div className="coverage-year-controls-v11"><button type="button" onClick={() => setYear((value) => value - 1)}>‹</button><strong>{year}</strong><button type="button" onClick={() => setYear((value) => value + 1)}>›</button></div></div>
    <div className="coverage-legend-v11"><span><i className="confirmed"></i>Confirmed</span><span><i className="partial"></i>Partial / uncertain</span><span><i className="unknown"></i>Unknown</span></div>
    <div className="coverage-scroll-v11">{rows.length ? rows.map((row) => <AccountTimeline key={row.account.id} row={row} year={year} onViewImport={setSelectedImport}/>) : <p className="muted">No Account coverage is available yet. Import a bank CSV and confirm the period it represents.</p>}</div>
    <p className="muted coverage-principle-v11">No coverage does not mean $0 spending. It means Fynvo does not have enough source evidence to know.</p>
    {selectedImport && <ImportDetail batchId={selectedImport} onClose={() => setSelectedImport(null)} onSaved={load}/>} 
  </section>;
}

export { segmentForMonth };
