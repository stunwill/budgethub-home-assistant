# Fynvo v1.3.0 Release Notes

## Cash Flow Intelligence, Financial Calendar & Smart Forecasting

Fynvo v1.3.0 strengthens the forward-looking household finance experience introduced through the v1.x releases. The release extends the existing forecast engine rather than replacing it, preserving existing financial records and established workflows.

## Highlights

### Cash Flow Intelligence

A new Cash Flow Intelligence experience provides:

- projected household balance;
- per-account projected balances;
- expected income and expenses;
- forecast horizons from 7 days through 12 months;
- lowest projected balance;
- explainable forecast event breakdowns;
- clear separation between the current position and forecast values.

### Account safety buffers

Accounts can now have an optional minimum balance or safety buffer. Fynvo identifies the first forecast event expected to take an account below that threshold and reports:

- expected date;
- projected balance;
- configured safety buffer;
- expected shortfall;
- contributing event.

Negative account balances receive a stronger cash-shortfall warning showing how much additional money would be required to avoid the projected negative balance.

### Overdue obligations remain visible

Unresolved overdue bills are no longer allowed to disappear simply because their due date is in the past. They remain in the v1.3 projection until they are resolved through the underlying financial workflow or an occurrence override.

### Forecast occurrence overrides

v1.3 introduces occurrence-level forecast overrides so a specific scheduled occurrence can be adjusted without rewriting the recurring template.

An occurrence can be:

- given a different expected amount;
- rescheduled;
- marked due, overdue, paid or skipped;
- optionally applied to future occurrences where appropriate.

This supports cases such as a one-month mortgage variation while preserving the normal recurring amount for later months.

### Internal transfers

Transfers between Fynvo Accounts update the projected balances of the source and destination Accounts while having a net household cash-flow effect of $0.

Forecast starting balances also exclude future-dated transactions so a scheduled transfer is not counted before its forecast date and then counted again.

### Financial Calendar

The v1.3 Financial Calendar provides daily totals for:

- expected income;
- expected expenses;
- net movement;
- contributing financial events.

### Upcoming money

Upcoming events are grouped into:

- Overdue;
- Today;
- Tomorrow;
- Next 7 Days;
- Later This Month;
- Future.

### Future Purchase Simulator

The **Can I afford this?** simulator allows an isolated purchase scenario to be evaluated against the forecast without modifying production financial records.

It reports:

- projected Account balance before the purchase;
- projected balance immediately after the purchase;
- lowest projected balance afterwards;
- whether the Account safety buffer would be breached;
- whether a negative balance is predicted.

### Mobile experience

The v1.3 cash-flow surfaces include responsive layouts for phone, tablet and desktop widths, including compact summary cards and touch-friendly financial calendar and upcoming views.

## Data model and upgrade safety

v1.3.0 adds:

- `accounts.minimum_balance_cents`;
- `forecast_occurrence_overrides`.

The migration is additive and does not recreate existing accounts, transactions, recurring expenses, categories, cards or household identity records.

## API additions

The following authenticated endpoints are introduced under `/api/v1.3`:

- `GET /cash-flow`
- `GET /calendar`
- `GET /upcoming`
- `PUT /accounts/{account_id}/buffer`
- `POST /occurrence-overrides`
- `POST /purchase-simulator`

## Forecast transparency

Forecast information is a projection based on the financial records and schedules available to Fynvo. It should not be interpreted as a confirmed bank balance or guaranteed future outcome.

Internal transfers are explicitly household-neutral, overdue items are identified as overdue, and isolated simulations do not modify real records.

## Testing

v1.3.0 adds regression coverage for:

- authenticated access to new forecast routes;
- transfer neutrality at household level;
- per-account transfer projections;
- overdue bill retention;
- occurrence-only forecast overrides;
- Account safety-buffer warnings;
- isolated purchase simulation;
- calendar daily totals;
- frontend v1.3 route and responsive-layout contracts.

## Known limitations

The v1.3 release intentionally extends the existing architecture incrementally. The following remain appropriate follow-up areas rather than being represented as complete in this release:

- direct bank-feed confirmation of forecast events;
- saved named What-If scenarios beyond the existing scenario foundation;
- richer historical actual balance charting where historical balance snapshots are not available;
- automatic probabilistic confidence percentages;
- full record-level household permissions and comprehensive audit history, which remain separate security-governance work.
