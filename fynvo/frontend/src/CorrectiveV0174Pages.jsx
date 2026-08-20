import { useEffect, useMemo, useState } from 'react';

const api = (path) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } });

export function CategoriesPageV0174({ rangeDays, onEdit, money }) {
  const [rows, setRows] = useState([]);
  const [expanded, setExpanded] = useState(() => new Set());
  const [selected, setSelected] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api(`/corrective-v0174/categories/summary?range_days=${rangeDays}`).then(async (response) => response.ok ? response.json() : []).then((data) => { if (!cancelled) setRows(Array.isArray(data) ? data : []); });
    return () => { cancelled = true; };
  }, [rangeDays]);

  const byParent = useMemo(() => {
    const map = new Map();
    for (const row of rows) {
      const parent = row.parent_id == null ? null : Number(row.parent_id);
      if (!map.has(parent)) map.set(parent, []);
      map.get(parent).push(row);
    }
    for (const list of map.values()) list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
    return map;
  }, [rows]);

  const parents = byParent.get(null) || [];
  const toggle = (id) => setExpanded((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const open = async (row) => {
    setSelected(row);
    setLoadingEntries(true);
    const response = await api(`/corrective-v0174/categories/${row.id}/entries?range_days=${rangeDays}`);
    setEntries(response.ok ? await response.json() : []);
    setLoadingEntries(false);
  };

  return <section className="panel categories-v0174"><div className="panel-head"><div><h2>Categories</h2><p className="muted">Parent totals include their child categories for the selected date range.</p></div><button className="primary ghost" onClick={() => onEdit({ type: 'categories', label: 'New Category', row: { id: null }, values: { name: '', parent_id: '', category_type: 'expense', budget_relationship: 'independent', is_active: true, notes: '' } })}>+ Add</button></div>
    <div className="category-list-v0174">{parents.map((parent) => {
      const children = byParent.get(Number(parent.id)) || [];
      const isOpen = expanded.has(parent.id);
      return <div className="category-group-v0174" key={parent.id}><div className="category-row-v0174 parent"><button className="category-accordion-v0174" type="button" aria-expanded={isOpen} onClick={() => toggle(parent.id)}>{children.length ? (isOpen ? '▾' : '▸') : '•'}</button><button className="category-name-v0174" type="button" onClick={() => open(parent)}>{parent.name}</button><strong>{money(parent.total) || '$0.00'}</strong><button className="category-count-v0174" type="button" onClick={() => open(parent)}>{parent.entry_count} entries</button></div>
        {isOpen && children.map((child) => <div className="category-row-v0174 child" key={child.id}><span></span><button className="category-name-v0174" type="button" onClick={() => open(child)}>{child.name}</button><strong>{money(child.total) || '$0.00'}</strong><button className="category-count-v0174" type="button" onClick={() => open(child)}>{child.entry_count} entries</button></div>)}</div>;
    })}</div>
    {selected && <div className="modal-backdrop" role="presentation"><section className="modal detail-modal" role="dialog" aria-modal="true"><div className="panel-head"><div><h2>{selected.name}</h2><p className="muted">{selected.path}</p></div><button type="button" onClick={() => setSelected(null)}>×</button></div><div className="detail-grid"><div className="detail-item"><span>Total</span><strong>{money(selected.total) || '$0.00'}</strong></div><div className="detail-item"><span>Assigned entries</span><strong>{selected.entry_count}</strong></div></div><h3>Matching entries</h3>{loadingEntries ? <p>Loading…</p> : entries.length ? <div className="category-entry-list-v0174">{entries.map((entry) => <div className="list-row" key={`${entry.source_type}-${entry.id}`}><span>{entry.name}<small>{entry.source_type.replaceAll('_', ' ')} · {entry.date || 'No date'}</small></span><strong>{money(entry.amount) || '$0.00'}</strong></div>)}</div> : <p className="muted">No matching entries in this date range.</p>}<div className="modal-actions"><button type="button" onClick={() => setSelected(null)}>Close</button><button type="button" className="primary" onClick={() => { const row = selected; setSelected(null); onEdit({ type: 'categories', label: 'Category', row, values: { name: row.name || '', parent_id: row.parent_id || '', category_type: row.category_type || 'expense', budget_relationship: row.budget_relationship || 'independent', is_active: row.is_active ?? true, notes: row.notes || '' } }); }}>Edit</button></div></section></div>}
  </section>;
}

export function RecurringExpensesPageV0174({ data, rangeDays, onEdit, money, dateLabel, normaliseRecord }) {
  const [frequency, setFrequency] = useState('all');
  const [summary, setSummary] = useState(null);
  useEffect(() => {
    let cancelled = false;
    api(`/corrective-v0174/recurring/summary?range_days=${rangeDays}&frequency=${encodeURIComponent(frequency)}`).then(async (response) => response.ok ? response.json() : null).then((value) => { if (!cancelled) setSummary(value); });
    return () => { cancelled = true; };
  }, [rangeDays, frequency, data.recurring.length]);
  const rows = summary?.items || [];
  const frequencies = [...new Set((data.recurring || []).map((item) => item.frequency).filter(Boolean))].sort();
  return <section className="panel recurring-v0174"><div className="panel-head"><div><h2>Recurring Expenses</h2><p className="muted">The selected date range controls the scheduled total shown below.</p></div><button className="primary ghost" onClick={() => onEdit({ type: 'recurring', label: 'New Recurring Expense', row: { id: null }, values: normaliseRecord('recurring', {}) })}>+ Add</button></div><div className="recurring-toolbar-v0174"><div><span>Total in selected range</span><strong>{summary ? money(summary.total) : 'Loading…'}</strong><small>{summary ? `${summary.occurrence_count} scheduled occurrences` : ''}</small></div><label>Frequency<select value={frequency} onChange={(e) => setFrequency(e.target.value)}><option value="all">All frequencies</option>{frequencies.map((item) => <option key={item} value={item}>{String(item).replaceAll('_', ' ')}</option>)}</select></label></div>{rows.length ? <div className="table recurring-table-v0174"><div className="thead"><span>Next due</span><span>Name</span><span>Amount</span><span>Frequency</span><span></span></div>{rows.map((row) => <div className="tr" key={row.id}><span>{dateLabel(row.next_due_date)}</span><span>{row.name}<small>{row.category || 'Uncategorised'}</small></span><span>{money(row.amount) || 'Not set'}</span><span>{String(row.frequency || 'Not set').replaceAll('_', ' ')}</span><button onClick={() => onEdit({ type: 'recurring', label: 'Recurring Expense', row, values: normaliseRecord('recurring', row) })}>Edit</button></div>)}</div> : <p className="muted">No recurring expenses match this frequency.</p>}</section>;
}
