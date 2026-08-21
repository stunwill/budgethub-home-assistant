import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const app = readFileSync(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const styles = readFileSync(new URL('../src/v14.css', import.meta.url), 'utf8');

test('v1.4 removes the global fixed launcher and keeps tool destinations accessible', () => {
  assert.equal(app.includes('className="v11-launcher"'), false);
  for (const label of [
    'Cash Flow Intelligence',
    'Household',
    'Data Coverage',
    'Split Transaction',
    'Security & MFA',
    'Data Export',
  ]) {
    assert.equal(app.includes(label), true, `${label} should remain accessible`);
  }
  assert.equal(app.includes('fynvo-tools-menu-trigger'), true);
});

test('v1.4 tools menu is compact instead of a full-width content-obscuring panel', () => {
  assert.equal(styles.includes('.fynvo-tools-menu-shell'), true);
  assert.equal(styles.includes('width:min(280px'), true);
  assert.equal(styles.includes('bottom:18px'), true);
  assert.equal(styles.includes('pointer-events:none'), true);
});
