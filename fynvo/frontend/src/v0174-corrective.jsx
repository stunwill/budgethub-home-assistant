export const APP_VERSION_V0174 = '0.17.5';

export function categoryGroups(categories = []) {
  const rows = categories.filter((item) => item && item.is_active !== false && (!item.category_type || item.category_type === 'expense'));
  const byParent = new Map();
  for (const row of rows) {
    const parentId = row.parent_id == null ? null : Number(row.parent_id);
    if (!byParent.has(parentId)) byParent.set(parentId, []);
    byParent.get(parentId).push(row);
  }
  for (const list of byParent.values()) list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
  return (byParent.get(null) || []).map((parent) => ({ parent, children: byParent.get(Number(parent.id)) || [] }));
}

export function CategorySelect({ categories = [], value = '', onChange }) {
  const groups = categoryGroups(categories);
  return <select value={value || ''} onChange={onChange}>
    <option value="">Choose category</option>
    {groups.map(({ parent, children }) => <optgroup key={parent.id} label={parent.name}>
      {children.length ? children.map((child) => <option key={child.id} value={child.path || child.name}>↳ {child.name}</option>) : <option key={parent.id} value={parent.path || parent.name}>{parent.name}</option>}
    </optgroup>)}
  </select>;
}

export function CashFlowChartV0174({ baseline, expected, money, dateLabel, Empty }) {
  const points = baseline?.chart_points || [];
  const expectedPoints = expected?.chart_points || [];
  const all = [...points, ...expectedPoints];
  if (!all.length) return <Empty title="No forecast yet">Add income, recurring expenses, bills or planned spending to generate a forecast.</Empty>;
  const values = all.map((point) => Number(point.balance || 0));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = Math.max(max - min, 1);
  const padLeft = 18;
  const padRight = 4;
  const padTop = 6;
  const padBottom = 16;
  const plotWidth = 100 - padLeft - padRight;
  const plotHeight = 100 - padTop - padBottom;
  const line = (rows) => rows.map((point, index) => {
    const x = padLeft + (index / Math.max(rows.length - 1, 1)) * plotWidth;
    const y = padTop + plotHeight - ((Number(point.balance || 0) - min) / span) * plotHeight;
    return `${x},${y}`;
  }).join(' ');
  const yTicks = [max, min + span / 2, min];
  const dateRows = points.length ? points : expectedPoints;
  const indexes = [...new Set([0, Math.floor((dateRows.length - 1) / 2), Math.max(dateRows.length - 1, 0)])];
  return <div className="chart-wrap chart-with-axes" role="img" aria-label="Cash flow forecast chart with balance and date axes">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none">
      {yTicks.map((tick, index) => {
        const y = padTop + (index / 2) * plotHeight;
        return <g key={`y-${index}`}><line x1={padLeft} y1={y} x2={100 - padRight} y2={y}/><text className="axis-label axis-y" x={padLeft - 1} y={y + 1.5} textAnchor="end">{money(tick)?.replace('.00', '')}</text></g>;
      })}
      {indexes.map((index) => {
        const x = padLeft + (index / Math.max(dateRows.length - 1, 1)) * plotWidth;
        return <g key={`x-${index}`}><line x1={x} y1={padTop} x2={x} y2={padTop + plotHeight}/><text className="axis-label axis-x" x={x} y={97} textAnchor={index === 0 ? 'start' : index === dateRows.length - 1 ? 'end' : 'middle'}>{dateLabel(dateRows[index]?.date).replace(/\s\d{4}$/, '')}</text></g>;
      })}
      <polyline className="baseline" points={line(points)}/><polyline className="expected" points={line(expectedPoints)}/>
    </svg>
    <div className="chart-legend"><span><i className="solid"></i>Baseline Forecast</span><span><i className="dash"></i>Expected Forecast</span></div>
  </div>;
}
