# Fynvo v0.14.0, Insights & Financial Health

Fynvo v0.14.0 adds an explainable Financial Insights layer on top of the existing household finance data.

## Highlights

- New **Insights** destination with filters, evidence and drill-down actions.
- New **Financial Health** overview across Cash Flow, Budgets, Spending, Recurring Commitments, Income, Goals and Data Quality.
- Forecast shortfall and low-balance signals that reconcile to Cash Flow.
- Budget pace and projected-over-budget signals that reuse the Budget service.
- Comparable spending trends with one-off baseline exclusions respected.
- Recurring commitment monthly and annual equivalents.
- Income-versus-expected and guarded savings analysis.
- Goal ahead/behind and combined Goal-contribution pressure signals.
- Scenario impact signals showing end-balance and lowest-balance changes.
- Data-quality signals for uncategorised transactions, reconciliation backlog and stale bank data.
- Insight dismissal and automatic resolution of stale conditions.
- Overview Financial Health card that surfaces only the most important current signals.

## Explainability first

Every high-value Insight contains the comparison inputs or source evidence that caused it to be generated. The user can expand **Why Fynvo is showing this** and navigate to the relevant financial area.

Fynvo does not use an unexplained overall Financial Health score in v0.14.0. Component statuses remain visible independently.

## Privacy

v0.14.0 Insights use local deterministic calculations over the household's own Fynvo data. Household financial records are not sent to an external AI service as part of the Insights feature.

## Upgrade notes

The release adds the persistent `insights` schema and advances the internal schema version to 12. Existing Accounts, Transactions, Budgets, Goals, Scenarios, Bank Connections, authentication and imported data are preserved.

## Known limitations

- Low-balance review currently uses a documented $1,000 default threshold.
- Historical Insight retention is lightweight in this release.
- Production Australian CDR provider integration remains future work.
- Rich Reports, exports, household User Management, Audit Logs and per-record Change History remain production-readiness work.
