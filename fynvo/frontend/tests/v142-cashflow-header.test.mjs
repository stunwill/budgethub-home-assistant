import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const cashflow = readFileSync(new URL('../src/V13CashFlowPage.jsx', import.meta.url), 'utf8');
const styles = readFileSync(new URL('../src/v142.css', import.meta.url), 'utf8');
const main = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');

test('v1.4.2 loads accounts independently from Cash Flow requests', () => {
  assert.equal(cashflow.includes('async function loadAccounts()'), true);
  assert.equal(cashflow.includes("api('/accounts').then"), true);
  assert.equal(cashflow.includes('Promise.allSettled(['), true);
  assert.equal(cashflow.includes('setAccounts(Array.isArray(rows) ? rows : [])'), true);
});

test('v1.4.2 reports HTTP failures rather than hiding them behind a generic JSON failure', () => {
  assert.equal(cashflow.includes('async function readJson(response, label)'), true);
  assert.equal(cashflow.includes('if (!response.ok)'), true);
  assert.equal(cashflow.includes('Cash flow failed'), false);
  assert.equal(cashflow.includes("readJson(response, 'Cash flow')"), true);
});

test('v1.4.2 fixes the Fynvo mobile app bar above scrolling content', () => {
  assert.equal(main.includes("import './v142.css';"), true);
  assert.equal(styles.includes('.mobile-app-bar'), true);
  assert.equal(styles.includes('position:fixed'), true);
  assert.equal(styles.includes('z-index:30'), true);
  assert.equal(styles.includes('padding-top:76px'), true);
});
