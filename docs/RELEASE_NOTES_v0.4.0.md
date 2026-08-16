# Fynvo v0.4.0 - Income, Recurring Expenses & Bills

Fynvo v0.4.0 adds scheduled household finance on top of the v0.3.0 account and transaction ledger.

## Added

- Income source management.
- Recurring expense management.
- Incomplete recurring-expense records with missing-field indicators.
- Bills and financial obligations.
- Overdue, due-soon, due-today, paid and unknown bill status calculation.
- Priority and paid-through date support for bills.
- Week, Month, Pay Cycle and Year views.
- Excel-style Jan-Dec annual matrix.
- Clickable annual matrix cells showing the underlying records behind each total.
- Initial household recurring-expense seed data.
- Initial outstanding bills and obligations seed data.

## Changed

- Overview now uses scheduled income, recurring expenses and bills.
- Upcoming now combines income, recurring commitments, bills and overdue obligations.
- Unknown amounts and dates are preserved as pending rather than being treated as zero or invented dates.

## Security

- Income, recurring expense, bill and schedule APIs are protected by the existing authenticated session.
- Scheduled finance data is scoped to the authenticated user.

## Upgrade notes

Existing v0.3.0 account and transaction data is preserved. v0.4.0 adds new scheduled-finance tables and bumps the schema version to 4.

## Manual Home Assistant check

After installing the update:

```text
Home Assistant
→ Fynvo
→ Login
→ Overview
→ Recurring Expenses
→ Income
→ Bills
→ Week
→ Month
→ Pay Cycle
→ Year
```

Refresh the page through Home Assistant ingress and confirm the app remains open.

## Next release

The next planned release remains v0.5.0 Planned Spending.
