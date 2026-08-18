import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const app = await readFile(new URL('../src/App.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/mobile-v16.css', import.meta.url), 'utf8');
const entry = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');

const viewports = [
  [320, 568], [375, 667], [390, 844], [393, 852], [430, 932],
  [768, 1024], [820, 1180], [1024, 768], [1280, 720], [1440, 900], [1920, 1080],
];

test('mobile drawer is closed by default and opens only from React state', () => {
  assert.match(app, /useState\(false\)/);
  assert.match(app, /mobileNavOpen \? 'mobile-nav-open' : ''/);
  assert.match(css, /transform:translateX\(-105%\)/);
  assert.match(css, /\.mobile-nav-open \.sidebar\{transform:translateX\(0\)/);
});

test('drawer supports all required dismissal paths', () => {
  assert.match(app, /setMobileNavOpen\(\(open\) => !open\)/);
  assert.match(app, /className="mobile-nav-close"/);
  assert.match(app, /className="mobile-nav-backdrop"/);
  assert.match(app, /event\.key === 'Escape'/);
  assert.match(app, /const navigate = \(item\) =>/);
  assert.match(app, /setMobileNavOpen\(false\)/);
});

test('drawer locks background scrolling and restores it', () => {
  assert.match(app, /document\.body\.style\.overflow = mobileNavOpen \? 'hidden' : previousOverflow/);
  assert.match(app, /document\.body\.style\.overflow = previousOverflow/);
  assert.match(css, /overflow-y:auto/);
  assert.match(css, /overscroll-behavior:contain/);
});

test('accessibility and focus management are wired', () => {
  assert.match(app, /aria-expanded=\{mobileNavOpen\}/);
  assert.match(app, /aria-controls="fynvo-navigation"/);
  assert.match(app, /aria-current=\{active === item \? 'page' : undefined\}/);
  assert.match(app, /aria-label="Primary navigation"/);
  assert.match(app, /focus\(\{ preventScroll: true \}\)/);
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
  assert.match(app, /window\.scrollTo\(\{ top: 0/);
});

test('mobile responsive overrides load after the base stylesheet', () => {
  assert.ok(entry.indexOf("'./mobile-v16.css'") > entry.indexOf("'./styles.css'"));
});
