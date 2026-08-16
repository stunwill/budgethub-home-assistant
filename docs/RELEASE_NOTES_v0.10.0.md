# Fynvo v0.10.0 Release Notes

## Spending Intelligence

Fynvo now starts recognising patterns in transaction history while keeping the user in control.

### Added

- Merchant/payee normalisation service.
- User-managed merchant rules.
- User-managed categorisation rules.
- Category suggestions with confidence and evidence.
- Spending Intelligence review queue.
- Recurring expense detection.
- Recurring income detection.
- Recurring amount-change detection.
- Spending trend analysis by category.
- Higher-than-usual transaction detection.
- One-off baseline exclusion support.
- Merchant summary/detail data foundation.
- Safe historical rule preview and historical rule application.
- Local deterministic processing with no external analytics or AI calls.

### User control

Fynvo suggests rather than silently changing important financial data. Users can accept or dismiss suggestions, create recurring records from detected patterns, and preview historical rule effects before applying them.

### Compatibility

The intelligence pipeline is source-independent and can process manual transactions, CSV-imported transactions and future CDR/Open Banking transactions.

### Known limitations

- This is not a full Insights release.
- Missing expected recurrence detection remains conservative.
- Duplicate subscription detection is foundational.
- Broader financial-health insights remain planned for v0.14.0.
