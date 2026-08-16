# Financial Calendar and v0.7.0 UI Foundation

Fynvo v0.7.0 introduces the first cohesive product interface built around three views of household finance:

- **Overview**: concise household position and forecast summary.
- **Cash Flow**: detailed forward-looking forecast explanation.
- **Calendar**: chronological view of what money is expected to enter and leave the household.

## Financial Calendar

The Financial Calendar is a read/projection experience. It does not collapse income, recurring expenses, bills, Planned Spending or forecast estimates into one database table.

Calendar events are generated from the same forecast infrastructure introduced in v0.6.0 so dates and amounts remain consistent with Cash Flow projections, including effective-dated recurring amount changes.

Event types include:

- income
- recurring expenses
- bills and obligations
- Planned Spending
- estimated forecast events where Expected Forecast is selected

The calendar supports Day, Week and Month views.

## Event drill-down

Calendar and Cash Flow events open a detail modal showing:

- date
- amount
- source type
- category
- projected balance where available
- forecast classification
- calculation explanation where provided by the forecast service

## Categories

v0.7.0 introduces a category visibility foundation across Fynvo modules. Categories are surfaced from existing financial records without rewriting historical records.

Full two-level hierarchy editing and budget-linked category management remain planned for later releases.

## Design system

The v0.7.0 interface establishes reusable visual language for:

- dark navy sidebar navigation
- light workspace
- rounded cards
- financial KPI cards
- badges and semantic states
- cash-flow chart containers
- financial event lists
- calendar event cards
- modals and empty states
- responsive mobile/tablet layout

Semantic states include positive, negative, warning, critical, actual, committed, planned and estimated. Colour is supported with text labels and financial signs so meaning is not conveyed by colour alone.

## Known limitations

- Budgeting navigation is shown as upcoming only. Full budgeting remains v0.8.0.
- Reports, Insights and saved Scenarios are intentionally not implemented as full business features in v0.7.0.
- Category persistence and hierarchy management remain future work.
- The chart is intentionally simple and prioritises readability over advanced analytics.
