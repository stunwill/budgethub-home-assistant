# Fynvo v1.5.1

## Recurring Expenses UI refresh

Fynvo v1.5.1 focuses on making Recurring Expenses easier to scan and more useful for day-to-day household cash-flow planning.

### Highlights

- Redesigned Recurring Expenses interface based on the supplied desktop and mobile mock-ups.
- Consolidated search, date-range, frequency and Category filters.
- Added Scheduled Total, payment count and average-payment summary values based on the currently filtered scheduled payments.
- Added Next Payment and Largest Upcoming Expense visibility.
- Added a compact period breakdown that reconciles to the selected-period total.
- Replaced desktop record cards with a lightweight sortable table.
- Added textual Overdue, Today, Tomorrow and future due-date urgency states with actual dates retained.
- Improved Category, Amount and Frequency presentation for faster financial scanning.
- Replaced the grey Edit button with an accessible Actions menu while retaining the existing edit workflow.
- Added responsive mobile rows, search/filter controls, a mobile filter sheet and collapsible summary details.
- Added appropriate empty states when no recurring expenses exist or filters return no results.

### Calendar view

The existing general Financial Calendar does not yet provide the recurring-expense-specific interaction required for a production-quality List/Calendar switch. v1.5.1 therefore keeps List as the implemented view and does not expose a decorative or non-functional Calendar control.

### Data and migration

No database migration is required.

Recurring-expense rules remain authoritative records. Scheduled rows are generated from the existing recurring occurrence summary service and are not persisted as duplicate recurring-expense records.

Existing authentication, forecasting, recurrence generation, persistence, category relationships and Home Assistant ingress architecture are unchanged.

### Validation

Repository CI remains the authoritative automated validation gate. Installed Home Assistant ingress and final visual screenshot acceptance must be verified on a running Fynvo installation because those checks require the Home Assistant runtime and representative user data.
