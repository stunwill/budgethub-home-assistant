import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const page = fs.readFileSync(new URL('../src/V13CashFlowPage.jsx', import.meta.url), 'utf8');
const shell = fs.readFileSync(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const styles = fs.readFileSync(new URL('../src/v13-cashflow.css', import.meta.url), 'utf8');

test('v1.3 cash-flow surfaces are mounted from the authenticated shell', () => {
  assert.match(shell, /V13CashFlowPage/);
  assert.match(shell, /Cash Flow Intelligence/);
  assert.match(shell, /setV13CashFlowOpen/);
});

test('v1.3 page exposes forecast, calendar, upcoming and purchase simulation workflows', () => {
  assert.match(page, /\/v1\.3\/cash-flow/);
  assert.match(page, /\/v1\.3\/calendar/);
  assert.match(page, /\/v1\.3\/upcoming/);
  assert.match(page, /\/v1\.3\/purchase-simulator/);
  assert.match(page, /Can I afford this\?/);
  assert.match(page, /Projected, not confirmed/);
});

test('v1.3 page exposes all required standard forecast horizons', () => {
  for (const horizon of ['7d', '14d', '30d', '60d', '90d', '6m', '12m']) {
    assert.match(page, new RegExp(`'${horizon}'`));
  }
});

test('v1.3 styles include phone and tablet breakpoints', () => {
  assert.match(styles, /max-width: 980px/);
  assert.match(styles, /max-width: 430px/);
  assert.match(styles, /v13-calendar-grid/);
});
