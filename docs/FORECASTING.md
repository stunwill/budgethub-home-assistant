# Cash Flow Forecasting

Fynvo v0.6.0 introduces a reusable cash-flow forecast engine.

## Concepts

Fynvo keeps these concepts separate:

- **Actual**: money that has really moved through an account.
- **Committed**: known obligations such as income, recurring expenses and bills.
- **Planned**: intended future spending that is not yet actual.
- **Budget**: an allowance or limit. Full budgeting remains a later release.
- **Forecast**: Fynvo's projection of what is likely to happen.

## Baseline forecast

The baseline forecast uses information Fynvo explicitly knows:

- current account balances;
- recurring income;
- recurring expenses;
- bills and obligations;
- forecast-included Planned Spending;
- effective-dated future amount changes.

It processes events chronologically and calculates the projected balance after each event.

## Expected forecast

The expected forecast starts with the baseline and adds historical run-rate estimates where there is enough transaction history.

For v0.6.0, Fynvo uses trailing eight complete weeks of manual transaction history and excludes categories already represented by recurring expenses, bills or Planned Spending. Estimated entries are clearly marked as estimated.

## Effective-dated changes

Recurring income and recurring expenses can now have known future amount changes.

Example:

```text
Internet
$140 monthly -> $80 monthly from 1 Oct 2026
```

The recurrence anchor/date is preserved. The amount changes only once the effective date is reached.

## Forecast horizons

Supported horizons include:

- next 7 days;
- next 30 days;
- next 3 months;
- next 6 months;
- end of current calendar year;
- next 12 months;
- custom day horizons up to 730 days.

## Lowest balance and shortfalls

Each forecast includes:

- final forecast balance;
- lowest projected balance and date;
- first projected shortfall, where relevant;
- nearby events contributing to the shortfall.

Fynvo presents this as factual projection information, not financial advice.

## Scenarios

Scenario forecasts compare the baseline with temporary what-if changes.

Supported v0.6.0 scenario adjustments include:

- one-off income;
- one-off expense;
- hypothetical recurring expense;
- temporary recurring expense removal for calculation purposes;
- temporary amount adjustments through the forecast engine.

Scenarios do not modify real records.

## API

Key endpoints:

```text
GET  /api/forecast
GET  /api/forecast/drilldown
POST /api/forecast/scenario
GET  /api/effective-amount-changes
POST /api/effective-amount-changes
```

## Limitations

v0.6.0 does not implement full budgeting, CSV reconciliation, CDR/Open Banking, automated recurring-cost discovery or advanced financial advice.
