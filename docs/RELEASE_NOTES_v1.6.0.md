# Fynvo v1.6.0

## Recurring Expenses responsive UI/UX redesign

v1.6.0 builds directly on merged v1.5.1 and completes the approved Recurring Expenses responsive experience across desktop, tablet, mobile and Home Assistant ingress.

### Baseline carried forward from v1.5.1

v1.5.1 already introduced the first Recurring Expenses UI refresh, including:

- Search, Date Range, Frequency and Category filtering
- Scheduled total, payment count and average payment
- Next payment summary
- period breakdown
- Largest Upcoming Expense
- sortable desktop recurring-expense table
- compact mobile recurring-expense rows
- mobile filter sheet
- accessible actions menu
- responsive and empty-state coverage

v1.6.0 must preserve this working functionality rather than reimplement it from scratch.

### v1.6.0 completion scope

- bring desktop and mobile layouts into closer alignment with the approved design mock-ups
- refine the compact mobile primary summary and `View summary` disclosure pattern
- complete the expanded mobile Summary, including payment-status summary and Quick Actions when backed by real payment-status data
- show a real active-filter count on mobile
- extend the mobile filter bottom sheet for payment method/status and attention filters only when supported by the real backend model
- add a production-ready Recurring Expenses `List | Calendar` segmented view
- add recurring-specific Calendar month navigation
- render scheduled recurring occurrences on their due dates
- handle multiple scheduled payments on the same date without forcing horizontal page scrolling
- show selected-date payment detail and an Upcoming section beneath the calendar
- preserve active filters while switching between List and Calendar
- expose payment-status indicators only when backed by real Fynvo payment-handling semantics
- maintain accessibility and practical touch targets in Home Assistant ingress
- verify the mobile implementation against an iPhone 15 Pro-class effective viewport

### Data safety

This is primarily a presentation and interaction release. Existing recurring-expense records and v1.5.1 behaviour must be preserved. Any backend or schema changes must be additive, justified and covered by upgrade-path tests.

### Acceptance gates

Do not merge v1.6.0 until repository checks are green. Installed Home Assistant ingress and actual iPhone/mobile acceptance remain explicit manual gates where they cannot be proven by CI.
