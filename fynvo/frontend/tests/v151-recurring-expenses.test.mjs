import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

const page = fs.readFileSync(new URL('../src/RecurringExpensesPageV151.jsx', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/recurring-v151.css', import.meta.url), 'utf8');

const expectSource = (needle, message) => assert.ok(page.includes(needle), message || `Expected RecurringExpensesPageV151.jsx to contain ${needle}`);

test('v1.5.1 consolidates recurring expense filtering', () => {
  for (const text of ['Search expenses...', 'All frequencies', 'All categories', 'Clear filters']) expectSource(text);
  expectSource('const RANGE_OPTIONS = [7, 14, 30, 60, 90];', 'date-range options should include 7, 14, 30, 60 and 90 days');
  expectSource('Next {days} days', 'date-range labels should be generated from the supported range options');
  expectSource("setSearch(''); setRangeDays(DEFAULT_RANGE); setFrequency('all'); setCategory('all');", 'clear filters should restore all filter defaults');
});

test('v1.5.1 summary derives totals and count from the same filtered rows', () => {
  expectSource('const total = filtered.reduce((sum, row) => sum + Number(row.amount || 0), 0);');
  expectSource('count: filtered.length');
  expectSource('average: filtered.length ? total / filtered.length : null');
  expectSource("{ label: 'Next 7 days'");
  expectSource("{ label: 'Following 7 days'");
  expectSource("{ label: 'Later'");
});

test('v1.5.1 sorting uses actual values', () => {
  expectSource("if (sort.key === 'amount') result = Number(left.amount || 0) - Number(right.amount || 0);");
  expectSource("else result = compareText(isoDate(left.next_due_date), isoDate(right.next_due_date));");
  for (const field of ['next_due_date', 'name', 'amount', 'frequency']) expectSource(`field=\"${field}\"`);
});

test('v1.5.1 relative due states remain textual and accessible', () => {
  for (const text of ['OVERDUE', 'TODAY', 'TOMORROW', 'IN ${diff} DAYS']) expectSource(text);
  expectSource('aria-label={`Actions for ${row.name || \'recurring expense\'}`}');
  expectSource('role="columnheader"');
});

test('v1.5.1 includes explicit empty states and responsive layouts', () => {
  for (const text of ['No recurring expenses yet', 'No expenses match these filters', 'recurring-v151-mobile-list', 'recurring-v151-filter-sheet']) expectSource(text);
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /\.recurring-v151-table\{display:none\}/);
  assert.match(css, /\.recurring-v151-mobile-list\{display:block/);
});

test('v1.5.1 does not expose a decorative calendar control', () => {
  assert.equal(page.includes('List | Calendar'), false);
  assert.equal(page.includes('Calendar</button>'), false);
});
