const navigation = [
  'Overview',
  'Cash Flow',
  'Recurring Expenses',
  'Income',
  'Planned Spending',
  'Calendar',
  'Categories',
  'Reports',
  'Settings',
];

const summaryCards = [
  ['Income', '$0.00', 'Next 90 days'],
  ['Recurring Bills', '$0.00', 'Next 90 days'],
  ['Planned Spending', '$0.00', 'Next 90 days'],
  ['Projected Balance', '$0.00', 'End of 90 days'],
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">BudgetHub</div>
        <nav>
          {navigation.map((item, index) => (
            <button className={index === 0 ? 'nav-item active' : 'nav-item'} key={item}>
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <main className="content">
        <header className="page-header">
          <div>
            <p className="eyebrow">Financial overview</p>
            <h1>BudgetHub</h1>
            <p className="muted">Your household cash-flow forecast will appear here.</p>
          </div>
          <select defaultValue="90">
            <option value="30">Next 30 days</option>
            <option value="60">Next 60 days</option>
            <option value="90">Next 90 days</option>
          </select>
        </header>

        <section className="summary-grid">
          {summaryCards.map(([title, value, subtitle]) => (
            <article className="card" key={title}>
              <p className="card-label">{title}</p>
              <strong>{value}</strong>
              <span>{subtitle}</span>
            </article>
          ))}
        </section>

        <section className="panel forecast-placeholder">
          <div>
            <p className="eyebrow">Cash Flow Forecast</p>
            <h2>Ready for financial data</h2>
          </div>
          <p className="muted">
            Recurring expenses, income and planned purchases will be combined here into a dated running balance.
          </p>
        </section>
      </main>
    </div>
  );
}
