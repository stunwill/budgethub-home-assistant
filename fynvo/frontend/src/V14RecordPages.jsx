const statusLabel = (value) => String(value || 'active').replaceAll('_', ' ');

function RecordCard({ date, title, subtitle, amount, meta, status, onEdit }) {
  return <article className="v14-record-card">
    <div className="v14-record-date-row"><span>{date}</span>{status && <span className="v14-record-status">{status}</span>}</div>
    <div className="v14-record-main"><div><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}</div>{amount && <strong className="v14-record-amount">{amount}</strong>}</div>
    <div className="v14-record-footer"><span>{meta || ''}</span><button type="button" onClick={onEdit}>Edit</button></div>
  </article>;
}

function PageShell({ title, description, onAdd, children }) {
  return <section className="panel v14-record-page"><div className="panel-head"><div><h2>{title}</h2><p className="muted">{description}</p></div><button className="primary ghost" type="button" onClick={onAdd}>+ Add</button></div><div className="v14-record-list">{children}</div></section>;
}

export function BillsPageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord }) {
  return <PageShell title="Bills" description="Bills and one-off obligations, including overdue items." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={dateLabel(row.due_date)} title={row.name || row.provider || 'Bill'} subtitle={row.bill_type || row.provider || 'Uncategorised'} amount={money(row.amount)} meta={row.account_name || row.source_account || row.priority || ''} status={statusLabel(row.status)} onEdit={() => onEdit({ type: 'bills', label: 'Bill', row, values: normaliseRecord('bills', row) })}/>) : <p className="muted">No bills yet.</p>}</PageShell>;
}

export function IncomePageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord }) {
  return <PageShell title="Income" description="Recurring and expected household income." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={dateLabel(row.next_payment_date)} title={row.name || row.payer || 'Income'} subtitle={row.category || row.payer || 'Income'} amount={money(row.amount)} meta={row.frequency ? String(row.frequency).replaceAll('_', ' ') : row.account_name || ''} status={row.is_active === false ? 'inactive' : 'active'} onEdit={() => onEdit({ type: 'income', label: 'Income', row, values: normaliseRecord('income', row) })}/>) : <p className="muted">No income records yet.</p>}</PageShell>;
}

export function AccountsPageV14({ rows, onEdit, onAdd, money, normaliseRecord }) {
  return <PageShell title="Accounts" description="Household accounts and their current financial position." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={row.institution || 'Account'} title={row.name || 'Account'} subtitle={String(row.account_type || 'account').replaceAll('_', ' ')} amount={money(row.current_balance ?? row.opening_balance)} meta={row.minimum_balance ? `Safety buffer ${money(row.minimum_balance)}` : row.account_suffix ? `••••${row.account_suffix}` : ''} status={row.archived_at ? 'inactive' : 'active'} onEdit={() => onEdit({ type: 'accounts', label: 'Account', row, values: normaliseRecord('accounts', row) })}/>) : <p className="muted">No accounts yet.</p>}</PageShell>;
}

export function PlannedSpendingPageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord }) {
  return <PageShell title="Planned Spending" description="Planned and committed future purchases." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={dateLabel(row.planned_date)} title={row.name || 'Planned Spending'} subtitle={row.category || 'Uncategorised'} amount={money(row.estimated_amount)} meta={row.priority || ''} status={statusLabel(row.status)} onEdit={() => onEdit({ type: 'planned', label: 'Planned Spending', row, values: normaliseRecord('planned', row) })}/>) : <p className="muted">No planned spending yet.</p>}</PageShell>;
}
