# Fynvo v0.16.0 - Mobile Experience & Responsive Navigation

## Summary

v0.16.0 fixes the mobile application shell so Fynvo financial content is no longer pushed below a permanently expanded navigation menu on phone-sized displays.

The existing authoritative desktop sidebar/navigation is reused as an off-canvas mobile drawer. No second mobile application or duplicate destination list is introduced.

## Root cause

The v0.15.0 frontend used a responsive CSS breakpoint that changed the application shell to one column below 980px, but it left `.sidebar` in normal document flow and made it sticky. Navigation groups were then rendered in multiple columns. On an iPhone-sized viewport the entire sidebar therefore became a large block of page content above the selected financial page.

## Mobile navigation

Below 980px:

- navigation is closed by default;
- a compact Fynvo application bar provides a 44px touch-target menu control;
- the existing sidebar becomes a left off-canvas drawer;
- the drawer width is responsive, normally 86-88% of the viewport with a 350px maximum;
- a dimmed backdrop prevents interaction with the page behind the drawer;
- backdrop tap, Close, Escape and navigation selection dismiss the drawer;
- selecting a destination closes the drawer and returns the new primary page to the top;
- the underlying page is scroll-locked while the drawer is open;
- the drawer scrolls independently;
- breakpoint changes clear stale drawer/open/scroll-lock state;
- active navigation styling continues to use the existing selected-item treatment.

## iPhone and Home Assistant ingress behaviour

The mobile shell uses dynamic viewport height (`dvh`) with `vh` fallback and safe-area insets for the top and bottom of the drawer. Fixed positioning is scoped to Fynvo's own viewport so it remains compatible with the Home Assistant ingress webview/panel shell.

## Accessibility

- `aria-expanded` tracks the menu state;
- `aria-controls` links the menu button to the navigation drawer;
- the drawer exposes an accessible navigation label;
- Escape closes the drawer;
- focus moves into the open drawer and returns to the menu control on dismissal where appropriate;
- menu and close controls use 44px minimum touch targets;
- reduced-motion preference disables drawer/backdrop transitions.

## Responsive content refinements

- phone content padding is reduced so page information appears sooner;
- KPI grids stack progressively on narrow displays;
- forms become single-column on mobile;
- data tables use touch-friendly horizontal scrolling rather than squeezing desktop columns into unreadable widths;
- modals respect dynamic viewport height and safe areas and scroll internally;
- action rows wrap on narrow displays;
- a smaller 320-360px breakpoint keeps headers and cards usable;
- tablet/small-desktop widths retain a persistent but narrower sidebar where appropriate.

## Regression protection

The release retains v0.15.0 authentication lifecycle code unchanged except for version metadata. Backend authentication tests remain part of CI.

The repository does not currently contain the planned v0.15.0 Home Assistant financial sensor/entity implementation. v0.16.0 therefore does not invent or duplicate those entities. Existing Home Assistant add-on ingress packaging and protected APIs remain in place.

## Automated checks

Frontend CI now runs a dependency-free Node test suite covering the mobile navigation regression contract, required dismissal paths, scroll locking, accessibility wiring, viewport breakpoints, safe-area support and reduced-motion support before building the production frontend.

Manual acceptance through a real Home Assistant iPhone-sized ingress session remains required before declaring the mobile release gate fully passed.
