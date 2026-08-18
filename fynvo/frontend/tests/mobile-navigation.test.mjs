import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const controller = await readFile(new URL('../src/mobile-navigation.js', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/mobile-v16.css', import.meta.url), 'utf8');

const viewports = [
  [320, 568], [375, 667], [390, 844], [393, 852], [430, 932],
  [768, 1024], [820, 1180], [1024, 768], [1280, 720], [1440, 900], [1920, 1080],
];

test('mobile drawer is closed by default and opens only via state class', () => {
  assert.match(css, /transform:translateX\(-105%\)/);
  assert.match(css, /\.mobile-nav-open \.sidebar\{transform:translateX\(0\)/);
  assert.match(controller, /aria-expanded', 'false'/);
});

test('drawer supports all required dismissal paths', () => {
  assert.match(controller, /menuButton\.addEventListener\('click'/);
  assert.match(controller, /closeButton\.addEventListener\('click'/);
  assert.match(controller, /backdrop\.addEventListener\('click'/);
  assert.match(controller, /event\.key === 'Escape'/);
  assert.match(controller, /closest\('\.nav-group button'\)/);
});

test('drawer locks background scrolling and restores it', () => {
  assert.match(controller, /document\.body\.style\.overflow = 'hidden'/);
  assert.match(controller, /document\.body\.style\.overflow = previousOverflow/);
  assert.match(css, /overflow-y:auto/);
  assert.match(css, /overscroll-behavior:contain/);
});

test('accessibility and focus management are wired', () => {
  assert.match(controller, /aria-controls/);
  assert.match(controller, /aria-hidden/);
  assert.match(controller, /\.focus\(\{ preventScroll: true \}\)/);
  assert.match(css, /min-width:44px;min-height:44px/);
  assert.match(css, /prefers-reduced-motion:reduce/);
});

test('responsive implementation covers required viewport matrix categories', () => {
  assert.equal(viewports.length, 11);
  assert.ok(viewports.some(([width]) => width === 320));
  assert.ok(viewports.some(([width]) => width === 768));
  assert.ok(viewports.some(([width]) => width >= 1280));
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /@media\(max-width:360px\)/);
  assert.match(css, /@media\(min-width:981px\) and \(max-width:1180px\)/);
});

test('iPhone and Home Assistant webview safe-area handling is present', () => {
  assert.match(css, /100dvh/);
  assert.match(css, /safe-area-inset-top/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(controller, /window\.scrollTo\(\{ top: 0/);
});
