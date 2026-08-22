import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const app = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const payment = await readFile(new URL('../src/PaymentManagementV17.jsx', import.meta.url), 'utf8');
const accounts = await readFile(new URL('../src/V14RecordPages.jsx', import.meta.url), 'utf8');
const main = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');


test('production frontend loads Cards and scheduled payment data', () => {
  assert.match(app, /j\('\/cards/);
  assert.match(app, /j\('\/scheduled-payments/);
  assert.match(app, /j\('\/payments\/attention/);
  assert.match(app, /active === 'Cards'/);
  assert.match(main, /payment-v17\.css/);
});


test('recurring form uses payment method conditional sources instead of generic Account field', () => {
  assert.match(app, /RecurringPaymentFieldsV17/);
  assert.match(payment, /Payment Method/);
  assert.match(payment, /method === 'direct_debit'/);
  assert.match(payment, /Bank Account/);
  assert.match(payment, /method === 'automatic_card_payment'/);
  assert.match(payment, /Linked to account:/);
  const recurringStart = app.indexOf("if (type === 'recurring')");
  const billsStart = app.indexOf("if (type === 'bills')", recurringStart);
  const recurringBranch = app.slice(recurringStart, billsStart);
  assert.doesNotMatch(recurringBranch, /<Field label="Account">/);
});


test('Card CRUD is connected to existing Accounts and stores only last four digits', () => {
  assert.match(payment, /\/cards\/\$\{edit\.id\}/);
  assert.match(payment, /Linked Account/);
  assert.match(payment, /Last 4 Digits/);
  assert.match(payment, /pattern="\[0-9\]\{4\}"/);
  assert.match(payment, /Multiple|cards\.filter|account_id/);
  assert.match(accounts, /linked Cards/);
  assert.match(accounts, /Manage Cards/);
});


test('payment attention and reconciliation actions are wired', () => {
  assert.match(payment, /Payments requiring attention/);
  assert.match(payment, /Mark as paid/);
  assert.match(payment, /scheduled-payments\/\$\{paying\.id\}\/mark-paid/);
  assert.match(payment, /payments\/match-candidates/);
  assert.match(payment, /Confirm match/);
  assert.match(payment, /scheduled-payments\/\$\{row\.scheduled_payment_id\}\/match/);
});
