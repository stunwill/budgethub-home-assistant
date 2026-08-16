# Spending Intelligence

Fynvo v0.10.0 introduces local, explainable spending intelligence. It helps maintain cleaner transaction data and highlights patterns without silently changing important financial records.

## Principles

- Suggestions are user-controlled.
- Original transaction descriptions are preserved.
- Merchant and category rules are deterministic.
- Recurring detections are treated as detected until accepted.
- Dismissed suggestions are suppressed unless materially new evidence appears.
- No transaction history is sent to external AI or analytics services.

## Merchant normalisation

Transactions can keep their original bank description while Fynvo stores or suggests a cleaner merchant name.

Example:

- Original: `WOOLWORTHS 1234 MILDURA`
- Normalised merchant: `Woolworths`

Built-in seed recognition covers common examples such as Woolworths, Coles, Telstra, Powershop, Netflix, Spotify, Uber and Budget Direct. Users can create their own rules.

## Rules

Rules support:

- exact match
- contains
- prefix
- suffix
- regular expression for advanced users

Rule precedence is:

1. explicit user transaction override
2. specific active user rule, ordered by priority
3. broader active user rule
4. built-in deterministic seed
5. learned suggestion
6. no suggestion

Rules can be created, edited, disabled and deleted. Historical application requires explicit user action and can be previewed first.

## Category suggestions

Fynvo suggests categories from:

- active category rules
- normalised merchant history
- previous categorisations
- transaction description patterns
- linked/imported context where available

Every category suggestion includes supporting evidence, such as previous transaction counts.

## Recurring detection

Fynvo analyses transaction history for likely recurring expenses and income. It considers:

- merchant similarity
- amount consistency
- date cadence
- direction
- existing recurring expense or income records

Detected frequencies include weekly, fortnightly, every 4 weeks, monthly, quarterly and annual.

Detected items are not committed forecast items until accepted. Accepting a recurring expense creates a recurring expense record. Accepting recurring income creates an income source.

## Amount-change detection

If a recurring-like pattern appears to have changed amount, Fynvo creates a review suggestion.

Example:

- previous Telstra payments averaged `$140`
- last two payments averaged `$80`

Accepting an amount-change suggestion uses the existing effective-dated change architecture where a matching confirmed record exists.

## Trends

Trend analysis compares the latest 8 weeks against the previous 8 weeks by category. States are:

- increasing
- stable
- decreasing

A trend is only highlighted when there is enough comparable history and the change is meaningful.

## Unusual spending

Fynvo can flag higher-than-usual transactions when a transaction is materially above the recent category baseline. Each anomaly includes:

- current transaction amount
- baseline average
- percentage difference
- period/context used

## One-off exclusions

A transaction can be marked as excluded from statistical baselines. This does not delete it, hide it from actual spending or remove it from budgets. It only prevents unusual one-off spending from distorting future intelligence calculations.

## Review queue

The Spending Intelligence review queue can include:

- merchant normalisation suggestions
- category suggestions
- recurring expense detections
- recurring income detections
- recurring amount changes
- spending trends
- unusual transactions

Actions include accept, dismiss, create recurring record, apply category and review transactions depending on suggestion type.

## Limitations in v0.10.0

- Intelligence is deterministic and local, not AI-generated financial advice.
- Duplicate-subscription detection is foundational and conservative.
- Missing expected recurring transaction detection remains limited.
- Broader financial-health insights remain planned for v0.14.0.
- Australian Open Banking/CDR remains planned for v0.12.0.
