import { useEffect, useMemo, useRef, useState } from 'react';

const api = (path) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } });
const DAY_MS = 24 * 60 * 60 * 1000;
const DEFAULT_RANGE = 30;
const RANGE_OPTIONS = [7, 14, 30, 60, 90];

const isoDate = (value) => String(value || '').slice(0, 10);
const startOfDay = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(`${isoDate(value)}T00:00:00`);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
};
const dayDiff = (value, reference = new Date()) => Math.round((startOfDay(value) - startOfDay(reference)) / DAY_MS);
const titleCaseFrequency = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return 'Not set';
  if (/^every[_\s-]*28[_\s-]*days?$/i.test(raw)) return 'Every 28 days';
  if (/^annual(ly)?$/i.test(raw)) return 'Annually';
  return raw.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
};
const categoryName = (row, categories) => {
  if (row.category) return row.category;
  const match = categories.find((category) => Number(category.id) === Number(row.category_id));
  return match?.name || 'Uncategorised';
};
const relativeDue = (value, reference = new Date()) => {
  const diff = dayDiff(value, reference);
  if (diff < 0) return { label: 'OVERDUE', tone: 'danger', diff };
  if (diff === 0) return { label: 'TODAY', tone: 'warning', diff };
  if (diff === 1) return { label: 'TOMORROW', tone: 'warning', diff };
  return { label: `IN ${diff} DAYS`, tone: diff <= 7 ? 'soon' : 'normal', diff };
};
const compareText = (left, right) => String(left || '').localeCompare(String(right || ''), undefined, { sensitivity: 'base', numeric: true });

export function buildRecurringExpenseView({ rows = [], categories = [], search = '', category = 'all', frequency = 'all', sort = { key: 'next_due_date', direction: 'asc' }, referenceDate = new Date() }) {
  const query = search.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    const rowCategory = categoryName(row, categories);
    if (frequency !== 'all' && String(row.frequency) !== String(frequency)) return false;
    if (category !== 'all' && String(rowCategory) !== String(category)) return false;
    if (query && !`${row.name || ''} ${rowCategory}`.toLowerCase().includes(query)) return false;
    return true;
  });
  const direction = sort.direction === 'desc' ? -1 : 1;
  filtered.sort((left, right) => {
    let result = 0;
    if (sort.key === 'amount') result = Number(left.amount || 0) - Number(right.amount || 0);
    else if (sort.key === 'name') result = compareText(left.name, right.name);
    else if (sort.key === 'frequency') result = compareText(titleCaseFrequency(left.frequency), titleCaseFrequency(right.frequency));
    else result = compareText(isoDate(left.next_due_date), isoDate(right.next_due_date));
    if (result === 0) result = compareText(left.name, right.name);
    return result * direction;
  });
  const total = filtered.reduce((sum, row) => sum + Number(row.amount || 0), 0);
  const next = filtered.slice().sort((left, right) => compareText(isoDate(left.next_due_date), isoDate(right.next_due_date)))[0] || null;
  const largest = filtered.slice().sort((left, right) => Number(right.amount || 0) - Number(left.amount || 0))[0] || null;
  const breakdown = [
    { label: 'Next 7 days', rows: filtered.filter((row) => { const diff = dayDiff(row.next_due_date, referenceDate); return diff <= 7; }) },
    { label: 'Following 7 days', rows: filtered.filter((row) => { const diff = dayDiff(row.next_due_date, referenceDate); return diff > 7 && diff <= 14; }) },
    { label: 'Later', rows: filtered.filter((row) => dayDiff(row.next_due_date, referenceDate) > 14) },
  ].map((bucket) => ({ label: bucket.label, count: bucket.rows.length, total: bucket.rows.reduce((sum, row) => sum + Number(row.amount || 0), 0) }));
  return { rows: filtered, total, count: filtered.length, average: filtered.length ? total / filtered.length : null, next, largest, breakdown };
}

function SortButton({ label, field, sort, onSort, numeric = false }) {
  const active = sort.key === field;
  const symbol = active ? (sort.direction === 'asc' ? '↑' : '↓') : '↕';
  return <button type="button" className={`recurring-v151-sort ${numeric ? 'amount' : ''}`} onClick={() => onSort(field)} aria-label={`Sort by ${label}${active ? `, currently ${sort.direction === 'asc' ? 'ascending' : 'descending'}` : ''}`}>{label}<span aria-hidden="true">{symbol}</span></button>;
}

function DueDateStatus({ value, dateLabel }) {
  const status = relativeDue(value);
  return <div className={`recurring-v151-due ${status.tone}`}><strong>{status.label}</strong><small>{dateLabel(value)}</small></div>;
}

function FrequencyBadge({ value }) {
  return <span className="recurring-v151-frequency">{titleCaseFrequency(value)}</span>;
}

function ActionsMenu({ row, onEdit, normaliseRecord }) {
  const [open, setOpen] = useState(false);
  const shellRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onDocumentClick = (event) => { if (!shellRef.current?.contains(event.target)) setOpen(false); };
    const onKeyDown = (event) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDocumentClick);
    document.addEventListener('keydown', onKeyDown);
    return () => { document.removeEventListener('mousedown', onDocumentClick); document.removeEventListener('keydown', onKeyDown); };
  }, [open]);
  return <div className="recurring-v151-actions" ref={shellRef}><button type="button" className="recurring-v151-actions-trigger" aria-label={`Actions for ${row.name || 'recurring expense'}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}>⋯</button>{open && <div className="recurring-v151-actions-menu" role="menu"><button type="button" role="menuitem" onClick={() => { setOpen(false); onEdit({ type: 'recurring', label: 'Recurring Expense', row, values: normaliseRecord('recurring', row) }); }}>Edit</button></div>}</div>;
}

function EmptyState({ hasRecords, hasFilters, onAdd, onClear }) {
  if (!hasRecords) return <div className="recurring-v151-empty"><strong>No recurring expenses yet</strong><p>Add recurring bills, subscriptions and household commitments to start forecasting future expenses.</p><button type="button" className="primary" onClick={onAdd}>+ Add recurring expense</button></div>;
  return <div className="recurring-v151-empty"><strong>No expenses match these filters</strong><p>Try changing the date range or clearing your filters.</p>{hasFilters && <button type="button" onClick={onClear}>Clear filters</button>}</div>;
}

function FilterBar({ search, setSearch, rangeDays, setRangeDays, frequency, setFrequency, category, setCategory, frequencies, categories, hasFilters, onClear, mobileFiltersOpen, setMobileFiltersOpen }) {
  const controls = <><input aria-label="Search recurring expenses" className="recurring-v151-search" type="search" placeholder="Search expenses..." value={search} onChange={(event) => setSearch(event.target.value)}/><select aria-label="Recurring expenses date range" value={rangeDays} onChange={(event) => setRangeDays(Number(event.target.value))}>{RANGE_OPTIONS.map((days) => <option key={days} value={days}>Next {days} days</option>)}</select><select aria-label="Recurring expenses frequency" value={frequency} onChange={(event) => setFrequency(event.target.value)}><option value="all">All frequencies</option>{frequencies.map((item) => <option key={item} value={item}>{titleCaseFrequency(item)}</option>)}</select><select aria-label="Recurring expenses category" value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All categories</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select><button type="button" className="recurring-v151-clear" disabled={!hasFilters} onClick={onClear}>Clear filters</button></>;
  return <><div className="recurring-v151-filterbar">{controls}</div><div className="recurring-v151-mobile-filterbar"><input aria-label="Search recurring expenses" className="recurring-v151-search" type="search" placeholder="Search expenses..." value={search} onChange={(event) => setSearch(event.target.value)}/><button type="button" className="recurring-v151-filter-button" aria-expanded={mobileFiltersOpen} onClick={() => setMobileFiltersOpen(true)}>Filters<span>{hasFilters ? '•' : ''}</span></button></div>{mobileFiltersOpen && <div className="modal-backdrop recurring-v151-filter-sheet-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setMobileFiltersOpen(false); }}><section className="recurring-v151-filter-sheet" role="dialog" aria-modal="true" aria-labelledby="recurring-filter-title"><div className="recurring-v151-filter-sheet-head"><strong id="recurring-filter-title">Filters</strong><button type="button" aria-label="Close filters" onClick={() => setMobileFiltersOpen(false)}>×</button></div><label><span>Date range</span><select value={rangeDays} onChange={(event) => setRangeDays(Number(event.target.value))}>{RANGE_OPTIONS.map((days) => <option key={days} value={days}>Next {days} days</option>)}</select></label><label><span>Frequency</span><select value={frequency} onChange={(event) => setFrequency(event.target.value)}><option value="all">All frequencies</option>{frequencies.map((item) => <option key={item} value={item}>{titleCaseFrequency(item)}</option>)}</select></label><label><span>Category</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All categories</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><div className="recurring-v151-filter-sheet-actions"><button type="button" disabled={!hasFilters} onClick={onClear}>Clear all</button><button type="button" className="primary" onClick={() => setMobileFiltersOpen(false)}>Show results</button></div></section></div>}</>;
}

function Summary({ view, rangeDays, money, dateLabel, expanded, setExpanded }) {
  return <section className={`recurring-v151-summary ${expanded ? 'is-expanded' : ''}`}><div className="recurring-v151-summary-main"><div className="recurring-v151-total"><span>Scheduled total</span><strong>{money(view.total) || '$0.00'}</strong><small>Scheduled in next {rangeDays} days</small><div><span>{view.count} {view.count === 1 ? 'payment' : 'payments'}</span>{view.average !== null && <span>{money(view.average)} avg</span>}</div></div><div className="recurring-v151-next"><span>Next payment</span>{view.next ? <><DueDateStatus value={view.next.next_due_date} dateLabel={dateLabel}/><div className="recurring-v151-next-row"><strong>{view.next.name}</strong><strong>{money(view.next.amount) || '$0.00'}</strong></div></> : <p>No upcoming payment in this period.</p>}</div></div><button type="button" className="recurring-v151-summary-toggle" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>{expanded ? 'Hide summary details' : 'Show summary details'}<span aria-hidden="true">{expanded ? '⌃' : '⌄'}</span></button><div className="recurring-v151-summary-details"><div className="recurring-v151-breakdown"><span>Breakdown by period</span>{view.breakdown.map((bucket) => <div key={bucket.label}><strong>{bucket.label}</strong><span>{money(bucket.total) || '$0.00'}<small>{bucket.count} {bucket.count === 1 ? 'payment' : 'payments'}</small></span></div>)}</div><div className="recurring-v151-largest"><span>Largest upcoming expense</span>{view.largest ? <><strong>{view.largest.name}</strong><p>{money(view.largest.amount)} · {dateLabel(view.largest.next_due_date)}</p></> : <p>No payment in this period.</p>}</div></div></section>;
}

export default function RecurringExpensesPageV151({ data, rangeDays: globalRangeDays, onEdit, money, dateLabel, normaliseRecord }) {
  const [rangeDays, setRangeDays] = useState(() => RANGE_OPTIONS.includes(globalRangeDays) ? globalRangeDays : DEFAULT_RANGE);
  const [search, setSearch] = useState('');
  const [frequency, setFrequency] = useState('all');
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState({ key: 'next_due_date', direction: 'asc' });
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api(`/corrective-v0174/recurring/summary?range_days=${rangeDays}&frequency=all`).then(async (response) => response.ok ? response.json() : null).then((value) => {
      if (cancelled) return;
      setSummary(value);
      setLoading(false);
    }).catch(() => { if (!cancelled) { setSummary(null); setLoading(false); } });
    return () => { cancelled = true; };
  }, [rangeDays, data.recurring.length]);

  const rawRows = summary?.items || [];
  const frequencies = useMemo(() => [...new Set((data.recurring || []).map((item) => item.frequency).filter(Boolean))].sort(compareText), [data.recurring]);
  const categoryOptions = useMemo(() => [...new Set((data.categories || []).filter((item) => item.is_active !== false && (!item.category_type || item.category_type === 'expense')).map((item) => item.name).filter(Boolean))].sort(compareText), [data.categories]);
  const view = useMemo(() => buildRecurringExpenseView({ rows: rawRows, categories: data.categories || [], search, category, frequency, sort }), [rawRows, data.categories, search, category, frequency, sort]);
  const hasFilters = search.trim() !== '' || rangeDays !== DEFAULT_RANGE || frequency !== 'all' || category !== 'all';
  const clearFilters = () => { setSearch(''); setRangeDays(DEFAULT_RANGE); setFrequency('all'); setCategory('all'); };
  const changeSort = (key) => setSort((current) => current.key === key ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: 'asc' });
  const addRecurring = () => onEdit({ type: 'recurring', label: 'New Recurring Expense', row: { id: null }, values: normaliseRecord('recurring', {}) });

  return <section className="recurring-v151-page"><div className="recurring-v151-page-head"><div><h2>Recurring Expenses</h2><p>Manage recurring bills, subscriptions and household commitments.</p></div></div><FilterBar search={search} setSearch={setSearch} rangeDays={rangeDays} setRangeDays={setRangeDays} frequency={frequency} setFrequency={setFrequency} category={category} setCategory={setCategory} frequencies={frequencies} categories={categoryOptions} hasFilters={hasFilters} onClear={clearFilters} mobileFiltersOpen={mobileFiltersOpen} setMobileFiltersOpen={setMobileFiltersOpen}/>{loading ? <div className="recurring-v151-loading" role="status">Loading recurring expenses…</div> : <><Summary view={view} rangeDays={rangeDays} money={money} dateLabel={dateLabel} expanded={summaryExpanded} setExpanded={setSummaryExpanded}/><div className="recurring-v151-results-head"><div><strong>Upcoming recurring expenses</strong><span>Scheduled payments generated from your recurring-expense rules</span></div></div>{view.rows.length ? <><div className="recurring-v151-table" role="table" aria-label="Upcoming recurring expenses"><div className="recurring-v151-table-head" role="row"><span role="columnheader"><SortButton label="Next due" field="next_due_date" sort={sort} onSort={changeSort}/></span><span role="columnheader"><SortButton label="Name" field="name" sort={sort} onSort={changeSort}/></span><span role="columnheader">Category</span><span role="columnheader"><SortButton label="Amount" field="amount" sort={sort} onSort={changeSort} numeric/></span><span role="columnheader"><SortButton label="Frequency" field="frequency" sort={sort} onSort={changeSort}/></span><span role="columnheader" className="sr-only">Actions</span></div>{view.rows.map((row) => <div className="recurring-v151-table-row" role="row" key={`${row.id}-${row.next_due_date}`}><span role="cell"><DueDateStatus value={row.next_due_date} dateLabel={dateLabel}/></span><span role="cell" className="recurring-v151-name"><strong>{row.name || 'Recurring expense'}</strong></span><span role="cell" className="recurring-v151-category">{categoryName(row, data.categories || [])}</span><span role="cell" className="recurring-v151-amount">{money(row.amount) || 'Not set'}</span><span role="cell"><FrequencyBadge value={row.frequency}/></span><span role="cell"><ActionsMenu row={row} onEdit={onEdit} normaliseRecord={normaliseRecord}/></span></div>)}</div><div className="recurring-v151-mobile-list">{view.rows.map((row) => <article className="recurring-v151-mobile-row" key={`mobile-${row.id}-${row.next_due_date}`}><div className="recurring-v151-mobile-main"><div><DueDateStatus value={row.next_due_date} dateLabel={dateLabel}/><strong className="recurring-v151-mobile-name">{row.name || 'Recurring expense'}</strong></div><div className="recurring-v151-mobile-amount"><strong>{money(row.amount) || 'Not set'}</strong><ActionsMenu row={row} onEdit={onEdit} normaliseRecord={normaliseRecord}/></div></div><div className="recurring-v151-mobile-meta"><span>{categoryName(row, data.categories || [])}</span><FrequencyBadge value={row.frequency}/></div></article>)}</div></> : <EmptyState hasRecords={(data.recurring || []).length > 0} hasFilters={hasFilters} onAdd={addRecurring} onClear={clearFilters}/>}</>}</section>;
}
