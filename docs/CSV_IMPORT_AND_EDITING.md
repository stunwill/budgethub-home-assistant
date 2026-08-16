# Editing Records and CSV Import

## Editing records

Fynvo v0.9.0 makes existing financial records maintainable after creation.

Supported editable records:

- Accounts
- Transactions
- Categories
- Bills
- Recurring Expenses
- Income
- Planned Spending
- Budgets

Open the relevant list screen and use the row-level Edit action. The edit modal loads the current record values and saves through an authenticated update API.

## Correcting data vs changing the future

Some edits are simple corrections, such as fixing a spelling mistake or assigning a category.

Financial behaviour changes may affect history. For recurring income, recurring expenses and budgets, use an effective date when a change should apply going forward.

Example:

- Internet was `$140/month`
- It changes to `$80/month from 1 October`
- Historical months remain explainable
- The future change is stored as an effective-dated change

## CSV Import workflow

The CSV workflow is:

1. Select the destination account.
2. Upload or paste a CSV file.
3. Map CSV columns.
4. Preview parsed rows.
5. Review invalid rows, duplicates and suggested matches.
6. Confirm import.
7. Review reconciliation suggestions.
8. Accept matches where appropriate.

## Supported CSV formats

Fynvo supports common Australian bank export styles:

- `DD/MM/YYYY`
- `DD/MM/YY`
- `YYYY-MM-DD`
- separate Debit and Credit columns
- single signed Amount column

## Duplicate detection

Duplicate detection considers:

- destination account
- transaction date
- amount
- merchant/description similarity

Fynvo favours avoiding duplicates. Likely duplicates are skipped by default during import.

## Matching and reconciliation

Fynvo attempts to match imported transactions to:

- Bills
- Recurring Expenses
- Planned Spending

A reconciliation link records:

- expected amount
- actual amount
- variance
- source record type
- source record ID
- confidence
- review status

The original source record is preserved. The imported bank transaction is preserved as an Actual transaction.

## Import history

Each CSV import creates an import batch with:

- filename
- account
- total rows
- imported count
- skipped count
- duplicate count
- matched count
- failed count
- status

## Review queue

Suggested matches appear in the Review Queue. Accepting a match can:

- mark a Bill as paid
- mark Planned Spending as purchased
- link Actual transaction to expected record
- avoid double counting in forecasts and future reporting

## Security

CSV data is treated as untrusted text. Fynvo does not execute CSV content and applies basic size and filename controls.
