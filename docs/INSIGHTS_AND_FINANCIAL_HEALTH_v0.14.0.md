# Fynvo v0.14.0 Insights & Financial Health

Fynvo v0.14.0 turns existing household financial records into explainable signals. Insights do not replace Transactions, Budgets, Forecasts, Goals, Scenarios or Spending Intelligence as sources of truth. They reference those services and retain the evidence used to explain why a signal exists.

## Product rules

Fynvo Insights are designed to answer five questions:

1. What happened or is projected to happen?
2. Compared with what?
3. Why does the difference matter?
4. Which Fynvo records or calculations support it?
5. Where can the user inspect the underlying data?

Insights use neutral wording. v0.14.0 does not send household financial records to an external AI service and does not generate personal investment, refinancing or spending instructions.

## Insight importance

- **Warning**: a high-value condition such as a projected negative cash balance.
- **Attention**: a material condition worth reviewing, such as projected budget overspend or low cash balance.
- **Opportunity**: a meaningful positive change, such as a category tracking materially below budget.
- **Information**: useful context or data-quality information that does not imply an urgent problem.

Financial status is never communicated by colour alone. The UI pairs visual treatment with labels and text.

## Insight lifecycle

Insights can be:

- **New**
- **Reviewed**
- **Dismissed**
- **Resolved**

Each generated condition receives a deterministic fingerprint derived from the Insight type, related entity and material evidence. Dismissing an Insight suppresses that unchanged condition. If the underlying condition materially changes, Fynvo may create a new Insight with a different fingerprint.

When an active condition no longer exists after recalculation, the previous Insight becomes **Resolved** rather than remaining as a stale warning.

## Financial Health

Financial Health is a transparent collection of component statuses. Fynvo deliberately does not show an unexplained single score.

Current dimensions are:

- Cash Flow
- Budget Health
- Spending Stability
- Recurring Commitments
- Income
- Goals
- Data Quality

Each status is derived from active evidence-backed Insights for that financial dimension.

## Cash Flow Insights

### Projected shortfall

Uses the existing expected forecast. If the forecast drops below zero, Fynvo records:

- forecast shortfall date
- projected balance
- selected horizon
- nearby forecast events that help explain the pressure

The Insight must reconcile to the Cash Flow forecast for the same horizon.

### Low-balance threshold

The initial v0.14.0 low-balance review threshold is **$1,000**. A projected balance below the threshold is separate from a true negative-balance warning.

This threshold is intentionally explicit in the supporting evidence. A future release can expose household configuration without changing the underlying Insight model.

### Upcoming financial pressure

Fynvo compares scheduled outgoing commitments during the next 14 days with the average 14-day commitment level across the selected forecast horizon.

An Insight is generated only when the next 14-day amount is materially higher than the comparison level and exceeds a minimum materiality threshold.

## Budget Health

Budget Insights reuse the existing Budget analysis service.

Important values include:

- available budget
- actual
- committed
- planned
- forecast
- projected variance
- utilisation percentage
- period elapsed percentage
- budget relationship mode
- item counts

### Projected over budget

Formula:

`Projected variance = Forecast - Effective available budget`

A positive variance indicates projected overspend.

### Budget pace

Fynvo compares budget utilisation percentage with period elapsed percentage.

Example:

- Budget used: 74%
- Period elapsed: 48%

This can create an attention Insight because spending is being consumed faster than the period is progressing.

### Unbudgeted spending

Categories with financial activity but no active budget can create an informational Insight. The user remains in control of whether to create a Budget.

## Spending trends

v0.14.0 compares two adjacent eight-week windows for categories with enough transaction history.

For each category:

`Current weekly average = current 8-week total / 8`

`Previous weekly average = previous 8-week total / 8`

`Percent change = (current total - previous total) / previous total × 100`

A trend is not generated unless both comparison periods contain sufficient activity and the change is material.

Transactions explicitly marked as one-off/baseline-excluded remain part of Actual spending but are omitted from this behavioural trend baseline.

Transfers are handled by the existing transaction model and are not treated as ordinary spending.

## Spending Intelligence reuse

v0.14.0 does not implement a second anomaly or recurring-payment detector. It reuses evidence produced by the existing Spending Intelligence service for signals including:

- unusual spending
- recurring amount changes
- recurring expense detection
- recurring income detection
- existing spending-trend suggestions

Pattern-derived signals may include High, Medium or Low confidence when that classification is meaningful. Deterministic financial calculations do not display artificial confidence scores.

## Recurring commitment equivalents

Recurring commitments can be converted to a monthly equivalent for comparison:

- Weekly: `amount × 52 / 12`
- Fortnightly: `amount × 26 / 12`
- Every 4 weeks / 28 days: `amount × 13 / 12`
- Monthly: `amount`
- Quarterly: `amount / 3`
- Annual/Yearly: `amount / 12`

Annual equivalent:

`Monthly equivalent × 12`

These are clearly labelled equivalents. The underlying recurrence remains unchanged.

## Income health

Expected income uses Fynvo's scheduled Income records for the calendar month.

Actual income uses recorded Actual transactions classified as income, excluding obvious refund descriptions in the v0.14.0 calculation.

The comparison shows Expected, Actual and current variance. A missing or unmatched expected Income signal is phrased as a reconciliation state, not as an assertion that an employer or payer failed to pay.

## Savings rate

When the data is sufficiently complete, Fynvo can calculate:

`Savings rate = (Actual income - Actual expense) / Actual income × 100`

Fynvo does not present a confident savings rate when income is missing or current transaction categorisation is materially incomplete.

Transfers are not intended to become household income or expense in this calculation.

## Goal Health

Goal Insights reuse the Goal service's existing progress calculations.

Evidence can include:

- target amount
- current amount
- remaining amount
- target date
- required contribution
- current contribution
- contribution frequency
- forecast completion date
- calculated status

### Competing Goal contributions

Fynvo converts active Goal required contributions to a monthly equivalent and compares the total with the selected forecast's implied monthly net surplus.

The wording presents the numbers. It does not tell the household which Goal to cancel or deprioritise.

## Scenario impact

Scenario Insights reuse the existing isolated Scenario comparison service.

They can show:

- end-balance difference
- lowest-balance difference
- whether a new cash shortfall is created
- the Scenario horizon

Scenario calculations do not modify baseline financial records.

## Data Quality

v0.14.0 can surface:

- uncategorised transaction count and value
- reconciliation backlog
- stale connected-bank data

Data-quality warnings are important because incomplete or stale underlying information can reduce the reliability of higher-level analysis.

## APIs

Authenticated endpoints include:

- `POST /api/insights/refresh`
- `GET /api/insights`
- `GET /api/insights/financial-health`
- `GET /api/insights/{id}`
- `POST /api/insights/{id}/reviewed`
- `POST /api/insights/{id}/dismiss`

List filtering supports status, importance and category.

## Performance model

Insight rows store lifecycle state and evidence, not a duplicate accounting ledger. Core financial calculations continue to come from the existing domain services.

Generation is bounded by selected forecast horizons and comparison windows. The persistent Insight model allows future releases to move more recalculation to event-driven/background processing without changing the user-facing API.

## Privacy

v0.14.0 Insights are calculated locally from Fynvo data. No household financial transaction history is sent to an external AI service as part of this feature.

## Known limitations

- The low-balance threshold is currently a documented default rather than a household-configurable setting.
- Historical Insight retention/archival is intentionally lightweight and should be refined for long-lived production datasets.
- Production CDR provider integration remains separate from the mock/provider-neutral banking foundation.
- Richer reports, exports, User Management, Audit Logs and Record Change History remain production-readiness work.
