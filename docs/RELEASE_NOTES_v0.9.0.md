# Fynvo v0.9.0 Release Notes

## Focus

v0.9.0 completes the missing record-editing requirement from v0.8.0 and introduces CSV Import & Reconciliation.

## Record editing

Editing is now exposed for:

- Accounts
- Transactions
- Categories
- Bills
- Recurring Expenses
- Income
- Planned Spending
- Budgets

List screens expose an Edit action. Edit forms load current values, submit to update endpoints and refresh the application data after save.

For recurring income, recurring expenses and budgets, future-dated amount changes can be recorded through effective-dated change records so history is not silently rewritten.

## CSV Import & Reconciliation

The import workflow supports:

- Australian bank CSV text/file input
- Australian dates: DD/MM/YYYY, DD/MM/YY and YYYY-MM-DD
- column mapping for date, description, merchant, debit, credit and signed amount
- preview before import
- invalid-row reporting
- duplicate detection by date, amount, account and description
- category suggestions
- matching suggestions against Bills, Recurring Expenses and Planned Spending
- import batches
- import history
- reconciliation review queue
- Actual vs Expected variance recording

Imported rows become first-class Actual transactions. They are not isolated from the rest of Fynvo, so they feed Budgeting, Cash Flow, Forecasting and future Reports.

## Reconciliation model

Fynvo keeps source records separate:

- a Bill remains a Bill
- a Planned Spending item remains a Planned Spending item
- an imported transaction remains an Actual transaction

Reconciliation links them together and records expected amount, actual amount, variance, source type and confidence.

## Known limitations

- Initial matching requires user confirmation through the Review Queue.
- Rollback is supported by import batch traceability, but destructive rollback remains a future refinement.
- Rule learning, recurring-payment discovery, merchant intelligence and anomaly detection remain planned for v0.10.0.
- Australian Open Banking/CDR remains planned for v0.12.0.

## Manual acceptance checklist

Before merging, verify in Home Assistant ingress:

- Edit an existing Bill and refresh to confirm persistence.
- Edit a Recurring Expense and refresh to confirm persistence.
- Edit an Income record and refresh to confirm persistence.
- Edit a Planned Spending item and refresh to confirm persistence.
- Edit a Category and refresh to confirm persistence.
- Edit a Budget and refresh to confirm persistence.
- Edit a Transaction and refresh to confirm persistence.
- Upload or paste a test CSV.
- Map columns.
- Preview rows.
- Confirm duplicate detection.
- Complete an import.
- Confirm imported transactions appear in Transactions.
- Confirm reconciliation review items can be accepted without double counting.
