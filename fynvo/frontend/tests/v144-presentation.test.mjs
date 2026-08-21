import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const css = await readFile(new URL('../src/hardening-v17.css', import.meta.url), 'utf8');

test('recurring expenses uses only the page title and removes the inner add header', () => {
  assert.match(css, /\.recurring-v0174>\.panel-head\{display:none\}/);
  assert.match(css, /The above date range and the below frequency controls the scheduled total shown below\./);
});

test('upcoming cash flow values are explicitly labelled', () => {
  assert.match(css, /Scheduled amount/);
  assert.match(css, /Projected balance after/);
});

test('upcoming cash flow details action is styled as a compact record button', () => {
  assert.match(css, /\.cashflow-table \.event-action\{[^}]*border-radius:999px/);
  assert.match(css, /\.cashflow-table \.event-action\{[^}]*background:#ececec/);
});
