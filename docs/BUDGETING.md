# Fynvo Budgeting

Fynvo budgeting is built around the distinction between **Budget**, **Actual**, **Committed**, **Planned**, **Forecast** and **Scenario**.

A budget is not a transaction. It is a financial allowance, limit or target for a category, income stream, household area or period.

## Core concepts

- **Budget**: the amount the household intends or permits itself to spend or receive.
- **Actual**: recorded transactions that have already happened.
- **Committed**: known obligations such as recurring expenses and bills.
- **Planned**: specific future spending the household intends to make.
- **Forecast**: what Fynvo expects will happen using actuals, commitments, planned items and historical run-rate behaviour.
- **Scenario**: a hypothetical change that does not modify real records.

## Budget periods

v0.8.0 introduces first-class support for:

- weekly budgets;
- true fortnightly budgets anchored to a start date;
- monthly budgets;
- quarterly budgets;
- annual budgets.

Fortnightly budgets are not treated as half-month budgets. They are repeating 14-day periods from an anchor date.

## Annual allocation

Annual budgets remain true annual constraints.

Examples:

- Car Maintenance: `$2,400/year`
- Christmas: `$2,000/year`
- Home Maintenance: `$5,000/year`

Fynvo can display allocation equivalents such as weekly, fortnightly or monthly, but the underlying limit remains the annual amount unless the user creates separate budgets.

## Rollover

Rollover is stored separately from the base budget.

Example:

```text
Base Budget: $250
Rollover: +$35
Available: $285
Actual: $210
Remaining: $75
```

Negative rollover is configurable. If disabled, overspending in one period does not reduce the following period's available amount.

## Category hierarchy

v0.8.0 introduces category hierarchy foundations.

Examples:

```text
Utilities > Electricity
Utilities > Internet
Transport > Car > Registration
```

Historical records keep their original category text. Category hierarchy is used for budgeting and analysis roll-ups rather than rewriting past transactions.

## Budget relationship modes

### Independent

Parent and child budgets are tracked separately.

### Shared Parent Pool

The parent owns the available pool. Child actuals reduce the parent remaining amount.

### Parent Equals Sum of Children

The parent budget is derived from child budgets. The parent amount should not be edited independently in this mode.

## Date-range analysis

Fynvo supports two analysis modes.

### Native budget periods

Each budget is evaluated using its own true period.

### Normalised selected period

Budget allowance can be proportionally allocated to a selected date range where suitable for flexible spending.

Discrete commitments, such as bills due on a date, are not pro-rated. If a bill is due in the selected period, it counts in that period.

## Saved views and configurable tables

v0.8.0 adds reusable saved-view storage for future table and report customisation. Saved views can store:

- column order;
- column widths;
- visibility;
- sorting;
- filters;
- account selections;
- category selections;
- hierarchy expanded/collapsed state;
- selected metrics.

A Reset View operation restores the default view without changing financial data.

## Unbudgeted categories

Budget analysis identifies categories with actual activity but no budget, such as:

```text
Dining Out
No budget
Actual this period: $196
Action: Create Budget
```

Where enough data exists, Fynvo can show historical averages to help create sensible budgets.

## Known limitations in v0.8.0

- Full report export remains future scope.
- Full persistent drag-and-drop table UI is foundational rather than exhaustive.
- Saved views are available as a backend/user preference foundation.
- Full Home Assistant budget sensors are planned for v0.15.0.
