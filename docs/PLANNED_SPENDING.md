# Planned Spending

Fynvo v0.5.0 introduces the Planned layer.

```text
BUDGET
How much am I allowing myself to spend?

PLANNED
What do I currently expect or intend to spend?

ACTUAL
What actually happened?
```

A Planned Spending item is not an actual transaction. It remains planned until the user explicitly records actual activity or a future reconciliation workflow matches it against an imported bank transaction.

## Fields

Planned Spending supports:

- name;
- description;
- estimated amount;
- planned date;
- optional start/end dates;
- category;
- funding account;
- merchant/provider;
- priority;
- status;
- owner/funding group;
- Include in Forecast;
- notes.

Unknown amounts are stored as null and shown as pending. Unknown dates are stored as null and shown as date pending.

## Statuses

- Idea: something being considered.
- Wishlist: wanted but not committed.
- Planned: expected to occur.
- Committed: the household has committed to the spend.
- Purchased: the purchase happened, but no fake actual transaction is created.
- Cancelled: no longer expected and excluded from future totals.

## Include in Forecast

Include in Forecast controls whether the item contributes to scheduled financial totals.

Only forecast-included Planned or Committed records with known amount and date are included in Week, Month, Pay Cycle and Year totals. Idea, Wishlist, Purchased, Cancelled, excluded and incomplete items remain visible in Planned Spending but do not reduce scheduled forecast totals.

## Drill-down hierarchy

Fynvo financial views follow this hierarchy:

```text
Year
→ Month
→ Week
→ Individual financial record
```

No meaningful financial total should be a black box. Annual month cells, month weekly cells and month totals expose the records that make up their values.

## Month week rules

Month view uses Monday-Sunday calendar weeks. A month includes every Monday-Sunday week that intersects the selected month. Partial weeks at month boundaries are displayed clearly, and only entries that belong to the selected month contribute to that month.

For example, if a week spans 31 August to 6 September, August totals include 31 August entries only. September entries contribute to September.

## Aggregation rules

Period totals count these scheduled events:

- income occurrences;
- recurring expense occurrences;
- bill/obligation occurrences;
- forecast-included planned spending.

Fynvo does not count actual transactions in scheduled views yet, and it does not count both a recurring definition and a separate generated occurrence for the same commitment. CSV reconciliation remains a future release.
