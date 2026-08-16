# Fynvo v0.11.0 Release Notes

## Goals & Financial Planning

Fynvo now has first-class Financial Goals.

You can create, edit and complete Goals for savings targets, emergency funds, planned purchases, annual expenses and debt reduction targets. Each Goal tracks target amount, current amount, remaining amount, target date, priority, contribution frequency and current contribution.

Goal progress includes required weekly, fortnightly or monthly contributions, percentage complete, forecast completion date and an explainable calculated status such as on track, ahead or behind.

## Account Allocation

Goals support explicit account allocations so a shared savings account is not accidentally counted in full against multiple Goals. Fynvo can show allocated and unallocated savings by account.

## Contributions and What-If Planning

Goal contributions can be recorded manually. A What-If contribution endpoint lets users test a different weekly, fortnightly or monthly contribution and see the estimated completion date and forecast impact without changing the saved Goal.

## Planned Spending Link Foundation

Goals can be linked to Planned Spending records so Fynvo understands the relationship between saving for something and eventually spending the money.

## Overview Dashboard Modernisation

The Overview has been redesigned as a household financial command centre using the supplied dashboard mock-up as the visual reference.

The dashboard now includes:

- welcome header with the authenticated display name
- shared forecast/date range selector
- Available Cash
- Expected Income
- Scheduled Commitments
- Planned Spending
- Projected Balance
- Cash Flow Forecast chart
- Forecast Summary
- Upcoming Commitments
- Upcoming events
- Top Planned Spending with Quick Add
- Quick Stats
- Budget Overview
- Goals summary
- Spending Intelligence attention count

Development-oriented cards have been removed from the household Overview.

## Quick Add Improvements

Quick Add now uses type-specific forms for supported record types and surfaces better validation feedback when a save fails.

## Version

All app, frontend and Home Assistant add-on version references are updated to `0.11.0`.

## Manual acceptance still required

Before release, verify Goals, Quick Add and the redesigned dashboard in the running Home Assistant app, including mobile and ingress layouts.
