# Fynvo Insights & Financial Health

Fynvo v0.14.0 turns existing household financial records and calculations into explainable signals. Insights are local, deterministic and user-controlled. They do not replace the source financial records, and they do not provide regulated financial advice.

## Product principles

An Insight should answer five questions:

1. What happened?
2. Compared with what?
3. Why does it matter?
4. What data supports it?
5. Where can the user inspect the underlying data?

The `insights` table stores lifecycle state, evidence references and presentation metadata. It is not the source of truth for balances, budgets, forecasts, Goals, recurring expenses or transactions. Insight generation reuses the existing Forecast, Budget, Goal, Scenario, Spending Intelligence, Reconciliation and Bank Connection services.

## Insight model

Each Insight records:

- `insight_type`
- category
- title and neutral summary
- importance: `information`, `opportunity`, `attention`, or `warning`
- relevant period
- related entity type and ID where applicable
- evidence JSON
- supporting references
- confidence only for pattern-derived signals where useful
- action label and drill-down target
- lifecycle status: `new`, `reviewed`, `dismissed`, or `resolved`
- generated/updated timestamps
- user attribution for review/dismiss actions
- a deterministic fingerprint used for duplicate and dismissal suppression

### Lifecycle

`New` means the condition is active and has not been reviewed.

`Reviewed` means the user has acknowledged the Insight but the underlying condition is still active.

`Dismissed` suppresses the unchanged condition. If the material evidence changes enough to produce a different fingerprint, Fynvo may create a new Insight.

`Resolved` means the underlying condition no longer exists. Active dashboard warnings therefore do not persist after the financial data changes.

## Financial Health

Fynvo deliberately does not create an unexplained overall score. Financial Health is a set of transparent dimensions:

- Cash Flow
- Budget Health
- Spending Stability
- Recurring Commitments
- Income
- Goals
- Data Quality

Each dimension is derived from active Insights. A Warning takes precedence over Needs Attention, which takes precedence over Improving/Opportunity. When no material issue exists, the dimension uses a neutral status such as Healthy, On Track or Stable.

## Cash Flow Insights

Cash Flow Insights reuse the existing forecast engine.

### Projected shortfall

A warning is generated when the expected forecast first falls below zero. Evidence includes the shortfall balance, date, forecast horizon and nearby forecast events.

### Low-balance threshold

When there is no negative shortfall but the forecast minimum falls below the current review threshold, Fynvo creates a separate Attention Insight. v0.14.0 uses a sensible default threshold of AUD 1,000. A future preference surface can make this household-configurable without changing the underlying rule model.

### Upcoming financial pressure

The next 14 days of scheduled outgoings are compared with the average 14-day commitment level across the selected forecast horizon. An Insight is created only when the next 14-day total is materially above the comparison basis and is also large enough to avoid trivial alerts.

## Budget Health

Budget Insights reuse `analyse_budgets()` and therefore use the same values shown on the Budgeting screen.

### Budget pace

`Budget pace = utilisation percentage - elapsed-period percentage`

A pace Insight is only generated when utilisation is materially ahead of elapsed time.

### Projected variance

`Projected variance = Forecast - Available Budget`

Available Budget includes the applicable base budget and rollover values already calculated by the Budget service.

Parent/child category expenditure is not recalculated in the Insights service. The Budget service remains responsible for hierarchy and relationship modes such as Independent, Shared Parent Pool and Parent Equals Sum of Children.

## Spending trends

The initial v0.14.0 trend rule compares two adjacent rolling 8-week windows.

`Weekly average = Window expense total / 8`

`Trend % = (Current window - Previous window) / Previous window * 100`

The rule requires at least three transactions in both windows and suppresses changes smaller than 15%. Transactions marked as excluded from the Spending Intelligence baseline are excluded from the trend calculation, while remaining part of Actual spending, Budgets and Cash Flow.

Existing Spending Intelligence suggestions for unusual spending, recurring detection and recurring amount changes are reused instead of running duplicate detectors.

## Recurring Commitments

Fynvo converts each active recurring expense to a monthly equivalent for comparison and reporting:

- Weekly: `amount * 52 / 12`
- Fortnightly: `amount * 26 / 12`
- Every 4 weeks / 28 days: `amount * 13 / 12`
- Monthly: `amount`
- Quarterly: `amount / 3`
- Annual: `amount / 12`

`Annual equivalent = Monthly equivalent * 12`

These are labelled equivalents, not additional scheduled transactions.

Confirmed recurring records remain separate from pattern-derived recurring suggestions. Amount-change Insights reuse existing Spending Intelligence evidence where available.

## Income and savings

### Income vs expected

Scheduled income for the current month is compared with Actual income transactions received to date. The wording describes a reconciliation difference and does not claim that a payer or employer failed to pay.

### Savings rate

When data quality is sufficient:

`Net Savings = Actual Income - Actual Expense`

`Savings Rate = Net Savings / Actual Income * 100`

Transfers are not included because the calculation uses only income and expense transaction types. Transactions whose description indicates a refund are excluded from Actual Income. Fynvo does not publish a savings rate when there is no recorded income or when uncategorised transaction volume makes the result insufficiently reliable.

The v0.14.0 savings rate is therefore a household cash-flow indicator, not investment or financial advice.

## Goal Health

Goal Insights reuse the Goal progress service, including calculated Ahead, On Track and Behind status, required contribution and forecast completion date.

### Required contribution

The Goal service calculates the remaining target divided across remaining weekly, fortnightly or monthly periods.

### Goal competition

Required contributions across active Goals are converted to a monthly equivalent and compared with the average monthly change in the selected expected forecast.

The result is factual context. Fynvo does not state that a household can or cannot afford a Goal.

## Scenario Insights

Scenario Insights reuse the existing isolated Scenario comparison service. They can report:

- end-balance delta
- lowest-balance delta
- whether a new shortfall appears

Scenario adjustments never mutate baseline records.

## Data Quality Insights

v0.14.0 can surface:

- uncategorised expense transactions
- reconciliation review backlog
- stale connected-bank data

Data-quality Insights are important because category, merchant, savings and trend analysis can only be as reliable as the underlying data.

## Drill-down actions

Insight actions route users to the relevant existing Fynvo destination, for example:

- Cash Flow
- Budgeting
- Transactions
- Spending Intelligence
- Income
- Goals
- Scenarios
- Review Queue
- Accounts / Bank Connections foundation

Actions are non-destructive. Fynvo does not automatically create budgets, cancel recurring expenses or modify financial records from an Insight.

## Performance and freshness

Insight generation uses bounded history windows for trend and data-quality queries, database indexes on Insight lifecycle/category fields, existing aggregation services, and deterministic fingerprints for update/suppression.

The Dashboard consumes only a small prioritised set of active Insights. Detailed evidence remains on the Insights page.

The architecture is suitable for later incremental recalculation hooks after transaction import/edit, reconciliation, bank sync, Budget changes, Goal changes and Scenario changes. v0.14.0 keeps explicit refresh support and avoids creating a second source of truth.

## Privacy and limitations

All v0.14.0 Insight calculation is local to Fynvo. Household financial records are not sent to an external AI service.

Fynvo presents factual calculations and comparisons. It does not tell users to invest, refinance, cancel services, select products or follow generic savings rules.

Limitations in v0.14.0 include:

- the low-balance threshold is a sensible default rather than a full household preference UI;
- richer Reports remain future work;
- production Australian CDR provider connectivity remains future work;
- savings-rate reliability remains deliberately conservative;
- user-specific Insight review state is founded on current user attribution, while full household roles/permissions remain before v1.0;
- advanced incremental/background recalculation can be expanded as transaction history grows.
