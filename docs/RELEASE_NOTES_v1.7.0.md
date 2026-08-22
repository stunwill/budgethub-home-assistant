# Fynvo v1.7.0

## Payment handling, Card management and recurring payment reconciliation

v1.7.0 builds on the merged v1.6.0 Recurring Expenses responsive redesign and closes the gap between Fynvo's existing Card/payment backend foundations and the production user interface.

### Account → Card management

- Added production UI Card management against existing Fynvo Accounts.
- Cards retain the existing authoritative `Card.account_id → Account.id` relationship.
- Supports multiple Cards per Account, Card type, last four digits, active/inactive status and linked-account display.
- Full card numbers, CVV/CVC, PINs and online-banking credentials are not stored.
- Existing Card IDs and Account relationships are preserved.

### Recurring Expense payment handling

- Replaced the ambiguous generic Account field in the Recurring Expense form with Payment Handling and Payment Method controls.
- Direct Debit conditionally requires a Bank Account.
- Automatic Card Payment conditionally requires a Card and derives the linked Account from that Card.
- BPAY, Bank Transfer, Manual Payment, Cash, Other and Not Set do not require a Card or Account by default.
- Added Automatic/Manual payment handling and configurable automatic-payment confirmation grace period.
- Existing legacy Account relationships are preserved and are not automatically misclassified as Direct Debit without existing evidence.

### Scheduled Payments

- Added additive Scheduled Payment persistence separate from the Recurring Expense rule.
- Scheduled occurrences retain expected date/amount, payment method/handling and expected payment source.
- Added Upcoming, Due, Overdue, Expected Automatically, Automatic Payment Not Confirmed, Paid, Skipped and Cancelled lifecycle states.
- Automatic payments are not blindly marked Paid on their due date.
- Default automatic-payment confirmation grace period is 3 days.
- Recurrence-aware generation covers weekly, fortnightly, 28-day, monthly, quarterly, yearly and custom-day schedules through the scheduling horizon.

### Payment confirmation and reconciliation

- Added Payments requiring attention for Due, Overdue and unconfirmed automatic payments.
- Added Mark as Paid with actual paid date, amount and note while preserving expected values.
- Added Skip Payment as a distinct status rather than recording a false zero-value payment.
- Added transaction-to-Scheduled-Payment matching with High/Medium/Low confidence foundations.
- Matching records the actual transaction date/amount, confirmation source and matched transaction ID.
- One transaction cannot be silently matched to multiple Scheduled Payments.
- Confirmed merchant mappings can be retained as future matching evidence; rejected matches are not learned.
- Variable actual payment amounts preserve expected-vs-actual variance without changing the master Recurring Expense.

### Production frontend integration

- The active `main.jsx → AppV13.jsx → AppCorrectiveV0174.jsx` production path now loads Cards and Scheduled Payments.
- Added a Cards navigation surface and linked Card summaries on Accounts.
- Added payment attention to Overview and Scheduled Payment match review alongside CSV/reconciliation workflows.
- Recurring Expense Add/Edit now uses the current payment model rather than legacy `direct_debit`/generic Account presentation.
- Added responsive Card and payment workflow styling for desktop, tablet, mobile and Home Assistant ingress layouts.

### Migration and data safety

- Migration is additive and idempotent.
- Existing Accounts, Cards, Recurring Expenses, historical data and Card IDs are not recreated.
- `payment_handling` is backfilled from existing Payment Method only where the existing method provides reliable evidence.
- Existing scheduled/payment data is preserved if migration runs more than once.
- Rollback should use a Home Assistant/Fynvo backup taken before upgrade. The additive v1.7 tables/columns are intentionally not destructively removed by a downgrade.

### Validation

Automated regression coverage includes Card/account relationship behaviour, automatic/manual defaults, conditional payment sources, grace-period status rules, recurrence generation, Mark as Paid, Skip Payment, variable actual amounts, one-to-one transaction matching, migration idempotency and production frontend wiring.

Installed Home Assistant ingress, iPhone/mobile interaction and production screenshots remain manual release gates when they cannot be executed by repository CI.
