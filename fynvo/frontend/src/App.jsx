import { useEffect, useState } from 'react';
import './styles.css';

const api = (path, options = {}) =>
  fetch(`api${path}`, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

const nav = ['Overview', 'Accounts', 'Transactions', 'Cash Flow', 'Recurring Expenses', 'Income', 'Planned Spending', 'Calendar', 'Categories', 'Reports', 'Settings'];

function money(value) {
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value || 0));
}

function Field({ label, ...props }) {
  return <label className="field"><span>{label}</span><input {...props} /></label>;
}

function Empty({ title, children }) {
  return <div className="empty"><strong>{title}</strong><p>{children}</p></div>;
}

export default function App() {
  const [auth, setAuth] = useState(null);
  const [active, setActive] = useState('Overview');
  const [error, setError] = useState('');
  const [form, setForm] = useState({ username: '', display_name: '', password: '' });
  const [overview, setOverview] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [accountForm, setAccountForm] = useState({ name: '', account_type: 'transaction', institution: '', opening_balance: '0.00' });
  const [txForm, setTxForm] = useState({ account_id: '', date: new Date().toISOString().slice(0, 10), amount: '', transaction_type: 'expense', description: '' });

  async function loadAuth() {
    const res = await api('/auth/state');
    setAuth(await res.json());
  }

  async function loadData() {
    const [overviewRes, accountsRes, txRes] = await Promise.all([api('/dashboard/overview'), api('/accounts'), api('/transactions')]);
    if (overviewRes.ok) setOverview(await overviewRes.json());
    if (accountsRes.ok) setAccounts(await accountsRes.json());
    if (txRes.ok) setTransactions(await txRes.json());
  }

  useEffect(() => { loadAuth(); }, []);
  useEffect(() => { if (auth?.authenticated) loadData(); }, [auth?.authenticated]);

  async function submitAuth(e) {
    e.preventDefault();
    setError('');
    const endpoint = auth?.setup_required ? '/auth/setup' : '/auth/login';
    const payload = auth?.setup_required
      ? { username: form.username, display_name: form.display_name || form.username, password: form.password }
      : { username: form.username, password: form.password };
    const res = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) });
    if (!res.ok) {
      setError('Sign-in failed. Check the username and password.');
      return;
    }
    await loadAuth();
  }

  async function logout() {
    await api('/auth/logout', { method: 'POST' });
    setAuth({ authenticated: false, setup_required: false, user: null });
  }

  async function addAccount(e) {
    e.preventDefault();
    const res = await api('/accounts', { method: 'POST', body: JSON.stringify(accountForm) });
    if (res.ok) {
      setAccountForm({ name: '', account_type: 'transaction', institution: '', opening_balance: '0.00' });
      await loadData();
    }
  }

  async function addTransaction(e) {
    e.preventDefault();
    const res = await api('/transactions', { method: 'POST', body: JSON.stringify({ ...txForm, account_id: Number(txForm.account_id) }) });
    if (res.ok) {
      setTxForm({ account_id: '', date: new Date().toISOString().slice(0, 10), amount: '', transaction_type: 'expense', description: '' });
      await loadData();
    }
  }

  if (!auth) return <main className="login"><div className="login-card"><h1>Fynvo</h1><p>Loading...</p></div></main>;

  if (!auth.authenticated) {
    return (
      <main className="login">
        <form className="login-card" onSubmit={submitAuth}>
          <div className="mark">F</div>
          <h1>Fynvo</h1>
          <p>Know what's coming.</p>
          {auth.setup_required && <p className="notice">Create the first administrator account.</p>}
          <Field label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          {auth.setup_required && <Field label="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />}
          <Field label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {error && <p className="error">{error}</p>}
          <button className="primary">{auth.setup_required ? 'Create account' : 'Sign in'}</button>
        </form>
      </main>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="mark">F</span><div><strong>Fynvo</strong><small>Know what's coming.</small></div></div>
        <nav>{nav.map((item) => <button key={item} onClick={() => setActive(item)} className={active === item ? 'active' : ''}>{item}</button>)}</nav>
      </aside>
      <main className="content">
        <header className="header">
          <div><p className="eyebrow">Financial ledger</p><h1>{active}</h1><p>Welcome back, {auth.user?.display_name}.</p></div>
          <button onClick={logout}>Logout</button>
        </header>
        {active === 'Overview' && (
          <>
            <section className="cards">
              <article><span>Available Cash</span><strong>{money(overview?.summary?.available_cash)}</strong></article>
              <article><span>Assets</span><strong>{money(overview?.summary?.assets)}</strong></article>
              <article><span>Liabilities</span><strong>{money(overview?.summary?.liabilities)}</strong></article>
              <article><span>Net Position</span><strong>{money(overview?.summary?.net_position)}</strong></article>
            </section>
            <section className="panel"><h2>Recent transactions</h2>{transactions.length ? <TransactionTable rows={transactions.slice(0,5)} /> : <Empty title="No transactions yet">Add an account and record your first transaction.</Empty>}</section>
          </>
        )}
        {active === 'Accounts' && (
          <section className="panel">
            <h2>Accounts</h2>
            <form className="grid-form" onSubmit={addAccount}>
              <Field label="Name" value={accountForm.name} onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })} />
              <label className="field"><span>Type</span><select value={accountForm.account_type} onChange={(e) => setAccountForm({ ...accountForm, account_type: e.target.value })}><option value="transaction">Transaction / Everyday</option><option value="savings">Savings</option><option value="credit_card">Credit Card</option><option value="cash">Cash</option><option value="mortgage">Mortgage</option><option value="personal_loan">Personal Loan</option><option value="vehicle_loan">Vehicle Loan</option><option value="other_asset">Other Asset</option><option value="other_liability">Other Liability</option></select></label>
              <Field label="Institution" value={accountForm.institution} onChange={(e) => setAccountForm({ ...accountForm, institution: e.target.value })} />
              <Field label="Opening balance" value={accountForm.opening_balance} onChange={(e) => setAccountForm({ ...accountForm, opening_balance: e.target.value })} />
              <button className="primary">Add account</button>
            </form>
            {accounts.length ? <div className="account-list">{accounts.map((account) => <article className="row-card" key={account.id}><div><strong>{account.name}</strong><span>{account.account_type} · {account.institution || 'No institution'}</span></div><strong>{money(account.current_balance)}</strong></article>)}</div> : <Empty title="No accounts yet">Create the first account to start the ledger.</Empty>}
          </section>
        )}
        {active === 'Transactions' && (
          <section className="panel">
            <h2>Transactions</h2>
            <form className="grid-form" onSubmit={addTransaction}>
              <label className="field"><span>Account</span><select value={txForm.account_id} onChange={(e) => setTxForm({ ...txForm, account_id: e.target.value })}><option value="">Select account</option>{accounts.map((a) => <option value={a.id} key={a.id}>{a.name}</option>)}</select></label>
              <Field label="Date" type="date" value={txForm.date} onChange={(e) => setTxForm({ ...txForm, date: e.target.value })} />
              <label className="field"><span>Type</span><select value={txForm.transaction_type} onChange={(e) => setTxForm({ ...txForm, transaction_type: e.target.value })}><option value="expense">Expense / Debit</option><option value="income">Income / Credit</option></select></label>
              <Field label="Amount" value={txForm.amount} onChange={(e) => setTxForm({ ...txForm, amount: e.target.value })} />
              <Field label="Description" value={txForm.description} onChange={(e) => setTxForm({ ...txForm, description: e.target.value })} />
              <button className="primary">Add transaction</button>
            </form>
            {transactions.length ? <TransactionTable rows={transactions} /> : <Empty title="No transactions yet">Transactions represent actual financial activity.</Empty>}
          </section>
        )}
        {!['Overview', 'Accounts', 'Transactions'].includes(active) && <section className="panel"><Empty title={`${active} is planned`}>This module is listed in the roadmap and will be implemented in a future release.</Empty></section>}
      </main>
    </div>
  );
}

function TransactionTable({ rows }) {
  return <div className="table"><div className="thead"><span>Date</span><span>Description</span><span>Account</span><span>Amount</span></div>{rows.map((row) => <div className="tr" key={row.id}><span>{row.date}</span><span>{row.description}</span><span>{row.account_name}</span><strong className={Number(row.amount) >= 0 ? 'positive' : 'negative'}>{money(row.amount)}</strong></div>)}</div>;
}
