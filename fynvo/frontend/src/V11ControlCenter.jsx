import { useEffect, useMemo, useState } from 'react';
import DataCoveragePageV11 from './V11DataCoverage.jsx';
import './v11.css';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

function Field({ label, children }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function SecurityPage() {
  const [state, setState] = useState(null);
  const [enrolment, setEnrolment] = useState(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    const response = await api('/v11/mfa/state');
    setState(response.ok ? await response.json() : null);
  };
  useEffect(() => { load(); }, []);

  const requestEnrolment = async () => {
    setError('');
    const response = await api('/v11/mfa/enrol', { method: 'POST' });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not start MFA enrolment.'); return; }
    setEnrolment(payload);
    setMessage('Add the secret or QR-compatible URI to your authenticator, then verify a code.');
  };

  const activate = async () => {
    setError('');
    const response = await api('/v11/mfa/activate', { method: 'POST', body: JSON.stringify({ code }) });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not enable MFA.'); return; }
    setRecoveryCodes(payload.recovery_codes || []);
    setEnrolment(null);
    setCode('');
    setMessage('MFA is enabled. Save the recovery codes somewhere secure before leaving this page.');
    await load();
  };

  const disable = async () => {
    setError('');
    const response = await api('/v11/mfa/disable', { method: 'POST', body: JSON.stringify({ code }) });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not disable MFA.'); return; }
    setCode('');
    setRecoveryCodes([]);
    setMessage('MFA has been disabled and other sessions were revoked.');
    await load();
  };

  const regenerate = async () => {
    setError('');
    const response = await api('/v11/mfa/recovery/regenerate', { method: 'POST', body: JSON.stringify({ code }) });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not regenerate recovery codes.'); return; }
    setRecoveryCodes(payload.recovery_codes || []);
    setCode('');
    setMessage('New recovery codes generated. Previous unused codes are invalid.');
    await load();
  };

  const recoveryReset = async () => {
    setError('');
    const response = await api('/v11/mfa/admin-recovery-reset', { method: 'POST' });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Recovery reset was not permitted.'); return; }
    setCode('');
    setRecoveryCodes([]);
    setEnrolment(null);
    setMessage(payload.message);
    await load();
  };

  return <section className="panel v11-security-page">
    <div className="panel-head"><div><h2>Authentication & MFA</h2><p className="muted">Optional TOTP two-factor authentication works with standards-compatible authenticator apps and has no cloud dependency.</p></div></div>
    {error && <div className="v11-alert error" role="alert">{error}</div>}
    {message && <div className="v11-alert" role="status">{message}</div>}
    <div className="detail-grid">
      <div className="detail-item"><span>MFA</span><strong>{state?.enabled ? 'Enabled' : 'Disabled'}</strong></div>
      <div className="detail-item"><span>Recovery codes remaining</span><strong>{state?.recovery_codes_remaining ?? '—'}</strong></div>
      <div className="detail-item"><span>Administrator recovery</span><strong>{state?.administrator_recovery_mode ? 'Enabled' : 'Off'}</strong></div>
    </div>
    {!state?.enabled && !enrolment && <button type="button" className="primary" onClick={requestEnrolment}>Set up authenticator MFA</button>}
    {enrolment && <div className="v11-enrolment"><h3>Authenticator setup</h3><p>Add this secret to your authenticator app:</p><code>{enrolment.secret}</code><details><summary>Authenticator URI</summary><code className="wrap">{enrolment.otpauth_uri}</code></details><Field label="Verification code"><input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value)} placeholder="123456"/></Field><button type="button" className="primary" onClick={activate}>Verify and enable MFA</button></div>}
    {state?.enabled && <div className="v11-security-actions"><Field label="Authenticator or recovery code"><input autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value)} placeholder="Code required for security changes"/></Field><div><button type="button" onClick={regenerate}>Generate new recovery codes</button><button type="button" className="danger" onClick={disable}>Disable MFA</button></div></div>}
    {state?.administrator_recovery_mode && <div className="v11-recovery-box"><strong>Administrator recovery mode is active</strong><p>This controlled Home Assistant recovery path can reset MFA if the administrator would otherwise be locked out.</p><button type="button" onClick={recoveryReset}>Reset administrator MFA</button></div>}
    {recoveryCodes.length > 0 && <div className="v11-recovery-codes"><h3>Recovery codes</h3><p>Each code is single-use. These plaintext codes are shown only in this response, Fynvo stores only their hashes.</p><div>{recoveryCodes.map((item) => <code key={item}>{item}</code>)}</div></div>}
    {state?.storage_model && <p className="muted v11-storage-note">{state.storage_model}</p>}
  </section>;
}

function SplitEditor({ transactions, categories }) {
  const [transactionId, setTransactionId] = useState('');
  const [split, setSplit] = useState(null);
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const transaction = useMemo(() => transactions.find((item) => String(item.id) === String(transactionId)), [transactions, transactionId]);
  const load = async (id) => {
    if (!id) { setSplit(null); setRows([]); return; }
    setError('');
    const response = await api(`/v11/transactions/${id}/splits`);
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not load transaction splits.'); return; }
    setSplit(payload);
    setRows((payload.items || []).map((item) => ({ id: item.id, amount: item.amount, category_id: item.category_id || '', category_name: item.category_name || '', notes: item.notes || '' })));
  };
  useEffect(() => { load(transactionId); }, [transactionId]);

  const authoritative = Number(split?.transaction_amount || transaction?.amount || 0);
  const allocated = rows.reduce((sum, row) => sum + Number(row.amount || 0), 0);
  const remaining = Math.round((authoritative - allocated) * 100) / 100;
  const update = (index, key, value) => setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  const addRow = () => setRows((current) => [...current, { amount: remaining > 0 ? remaining.toFixed(2) : '', category_id: '', category_name: '', notes: '' }]);
  const removeRow = (index) => setRows((current) => current.filter((_, rowIndex) => rowIndex !== index));

  const save = async () => {
    setError('');
    setMessage('');
    if (Math.round(remaining * 100) !== 0) { setError(`Split must balance before saving. Remaining $${remaining.toFixed(2)}.`); return; }
    const payloadRows = rows.map((row) => ({ id: row.id, amount: row.amount, category_id: row.category_id || null, category_name: row.category_name || null, notes: row.notes || null }));
    const response = await api(`/v11/transactions/${transactionId}/splits`, { method: 'PUT', body: JSON.stringify({ items: payloadRows }) });
    const payload = await response.json().catch(() => null);
    if (!response.ok) { setError(payload?.detail || 'Could not save transaction split.'); return; }
    setMessage('Transaction split saved. Account balance and source provenance remain attached to the parent transaction.');
    await load(transactionId);
  };

  const clear = async () => {
    const response = await api(`/v11/transactions/${transactionId}/splits`, { method: 'DELETE' });
    if (!response.ok) { setError('Could not remove this split.'); return; }
    setMessage('Split allocations removed. The authoritative parent transaction was preserved.');
    await load(transactionId);
  };

  return <section className="panel v11-split-page"><div className="panel-head"><div><h2>Transaction Splitting</h2><p className="muted">Allocate one authoritative Actual transaction across multiple Categories without duplicating the transaction.</p></div></div>
    {error && <div className="v11-alert error" role="alert">{error}</div>}{message && <div className="v11-alert" role="status">{message}</div>}
    <Field label="Transaction"><select value={transactionId} onChange={(event) => setTransactionId(event.target.value)}><option value="">Choose transaction</option>{transactions.map((item) => <option key={item.id} value={item.id}>{item.date || item.transaction_date} · {item.description || item.merchant || 'Transaction'} · ${item.amount}</option>)}</select></Field>
    {split && <><div className="detail-grid"><div className="detail-item"><span>Authoritative amount</span><strong>${Number(authoritative).toFixed(2)}</strong></div><div className="detail-item"><span>Allocated</span><strong>${allocated.toFixed(2)}</strong></div><div className={`detail-item ${Math.round(remaining * 100) === 0 ? '' : 'attention'}`}><span>Remaining</span><strong>${remaining.toFixed(2)}</strong></div></div>
      <div className="v11-split-rows">{rows.map((row, index) => <div className="v11-split-row" key={row.id || `new-${index}`}><input aria-label={`Allocation ${index + 1} amount`} value={row.amount} onChange={(event) => update(index, 'amount', event.target.value)} placeholder="0.00"/><select aria-label={`Allocation ${index + 1} category`} value={row.category_id} onChange={(event) => { const selected = categories.find((category) => String(category.id) === event.target.value); update(index, 'category_id', event.target.value); update(index, 'category_name', selected?.name || ''); }}><option value="">Choose Category</option>{categories.filter((category) => category.is_active !== false).map((category) => <option key={category.id} value={category.id}>{category.path || category.name}</option>)}</select><input aria-label={`Allocation ${index + 1} notes`} value={row.notes} onChange={(event) => update(index, 'notes', event.target.value)} placeholder="Notes (optional)"/><button type="button" onClick={() => removeRow(index)}>Remove</button></div>)}</div>
      <div className="v11-inline-actions"><button type="button" onClick={addRow}>+ Add allocation</button><button type="button" disabled={!rows.length} onClick={clear}>Remove split</button><button type="button" className="primary" disabled={!rows.length || Math.round(remaining * 100) !== 0} onClick={save}>Save split</button></div>
    </>}
  </section>;
}

function ExportPage() {
  const [warningAccepted, setWarningAccepted] = useState(false);
  const datasets = ['accounts', 'cards', 'transactions', 'transaction_splits', 'categories', 'income', 'bills', 'recurring_expenses', 'planned_spending', 'budgets', 'goals', 'scenarios', 'import_batches', 'coverage_gaps', 'reconciliation_links'];
  const downloadJson = async () => {
    const response = await api('/v11/exports/full');
    if (!response.ok) return;
    const payload = await response.json();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `fynvo-export-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  return <section className="panel v11-export-page"><div className="panel-head"><div><h2>Data Portability</h2><p className="muted">Export authoritative Fynvo financial data in relationship-preserving JSON or dataset CSV.</p></div></div><div className="v11-alert warning"><strong>Sensitive financial data</strong><span>Exports can include account, transaction, budget and provenance information. Store exported files securely.</span></div><label className="v11-checkbox"><input type="checkbox" checked={warningAccepted} onChange={(event) => setWarningAccepted(event.target.checked)}/> I understand this export contains sensitive financial information.</label><div className="v11-export-actions"><button className="primary" type="button" disabled={!warningAccepted} onClick={downloadJson}>Download full JSON export</button>{datasets.map((dataset) => <a key={dataset} className={warningAccepted ? 'button-link' : 'button-link disabled'} aria-disabled={!warningAccepted} href={warningAccepted ? `api/v11/exports/${dataset}.csv` : undefined}>{dataset.replaceAll('_', ' ')} CSV</a>)}</div><p className="muted">JSON is the authoritative portability format because it preserves relationships that flat CSV cannot.</p></section>;
}

export default function V11ControlCenter({ mode, onClose }) {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  useEffect(() => {
    if (mode !== 'splits') return;
    Promise.all([
      api('/transactions?limit=500').then((response) => response.ok ? response.json() : []),
      api('/categories').then((response) => response.ok ? response.json() : []),
    ]).then(([transactionRows, categoryRows]) => { setTransactions(transactionRows || []); setCategories(categoryRows || []); });
  }, [mode]);
  return <main className="v11-control-centre"><div className="v11-control-head"><div><strong>Fynvo v1.1.0</strong><span>{mode === 'coverage' ? 'Financial Data Coverage' : mode === 'security' ? 'Security' : mode === 'splits' ? 'Transaction Splitting' : 'Data Export'}</span></div><button type="button" onClick={onClose}>Back to Fynvo</button></div><div className="v11-control-content">{mode === 'coverage' && <DataCoveragePageV11/>}{mode === 'security' && <SecurityPage/>}{mode === 'splits' && <SplitEditor transactions={transactions} categories={categories}/>} {mode === 'export' && <ExportPage/>}</div></main>;
}
