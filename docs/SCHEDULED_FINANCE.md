# Scheduled Finance

Fynvo v0.4.0 introduces scheduled financial records while keeping them separate from actual transactions.

## Record types

### Income

Income sources describe money expected to arrive, such as wages, salary, allowances or one-off income. Income supports weekly, fortnightly, every-28-days, every-four-weeks, monthly, quarterly, yearly, custom and one-off schedules.

### Recurring Expense

Recurring expenses describe commitments that repeat, such as mortgages, insurance, subscriptions, utilities and savings contributions. A recurring expense may be complete or incomplete.

A complete recurring expense has enough information to generate dated expected occurrences:

- amount;
- frequency;
- next due or payment date;
- account link where known.

An incomplete recurring expense is still saved and visible. Fynvo reports missing fields rather than discarding the record or turning unknown values into zero.

Active/inactive is separate from completeness. An inactive record may still be complete or incomplete.

### Bill / Financial Obligation

Bills and obligations are one-off or current amounts owed. They can represent upcoming bills, overdue bills, arrears, missed payments or payment-plan candidates.

Bills support:

- provider/payee;
- priority;
- amount or unknown amount;
- due date or unknown date;
- paid-through date;
- notes;
- relationship to a recurring expense where known.

## Actual Transactions

Transactions remain actual financial activity. A recurring bill becoming due does not automatically create an actual transaction. Future CSV reconciliation will match imported actual bank transactions against these expected scheduled records.

## Unknown values

Unknown amounts are shown as pending and are stored as null. Unknown dates are shown as date pending and make the record incomplete. Fynvo does not invent due dates.

## Overdue behaviour

Bills with due dates are evaluated dynamically from the current date. Historical labels such as `NOT DUE`, `DUE NOW` and `OVERDUE` are preserved only as source metadata and are not treated as permanently authoritative.

Overdue records remain visible after their due date.

## Views

Fynvo v0.4.0 includes:

- Week view;
- Month view;
- Pay Cycle view;
- Year view;
- Jan-Dec annual matrix.

The annual matrix groups scheduled records by category and item. Clicking any monthly cell opens a drill-down showing the records that make up that value.

## Initial data

The v0.4.0 seed data includes Stu's supplied household recurring expenses and outstanding bills. Account names such as `KW ING Everyday` and `ING Everyday` are preserved as source account text when there is no unambiguous Fynvo account match.
