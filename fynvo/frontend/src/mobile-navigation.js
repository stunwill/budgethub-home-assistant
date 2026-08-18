const MOBILE_QUERY = '(max-width: 980px)';
const RELEASE_VERSION = '0.16.0';

function isMobileViewport() {
  return window.matchMedia(MOBILE_QUERY).matches;
}

function getShellParts() {
  const shell = document.querySelector('.shell');
  if (!shell) return null;
  return {
    shell,
    sidebar: shell.querySelector('.sidebar'),
    content: shell.querySelector('.content'),
  };
}

function ensureMobileNavigation() {
  const parts = getShellParts();
  if (!parts?.sidebar || !parts?.content) return;
  const { shell, sidebar, content } = parts;

  document.querySelectorAll('.eyebrow').forEach((node) => {
    if (/^Fynvo v/i.test(node.textContent || '')) node.textContent = `Fynvo v${RELEASE_VERSION}`;
  });

  if (shell.dataset.mobileNavReady === 'true') return;
  shell.dataset.mobileNavReady = 'true';

  const toolbar = document.createElement('div');
  toolbar.className = 'mobile-app-bar';
  toolbar.setAttribute('aria-label', 'Fynvo application controls');

  const menuButton = document.createElement('button');
  menuButton.type = 'button';
  menuButton.className = 'mobile-menu-button';
  menuButton.setAttribute('aria-label', 'Open Fynvo navigation');
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-controls', 'fynvo-navigation');
  menuButton.innerHTML = '<span aria-hidden="true">☰</span><span class="sr-only">Menu</span>';

  const identity = document.createElement('strong');
  identity.className = 'mobile-app-identity';
  identity.textContent = 'Fynvo';

  toolbar.append(menuButton, identity);
  content.prepend(toolbar);

  sidebar.id = 'fynvo-navigation';
  sidebar.setAttribute('aria-label', 'Fynvo navigation');
  sidebar.setAttribute('aria-hidden', 'true');

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.className = 'mobile-nav-close';
  closeButton.setAttribute('aria-label', 'Close Fynvo navigation');
  closeButton.innerHTML = '<span aria-hidden="true">×</span>';
  sidebar.prepend(closeButton);

  const backdrop = document.createElement('button');
  backdrop.type = 'button';
  backdrop.className = 'mobile-nav-backdrop';
  backdrop.setAttribute('aria-label', 'Close Fynvo navigation');
  backdrop.tabIndex = -1;
  shell.append(backdrop);

  let previousOverflow = '';

  const setOpen = (open, { restoreFocus = true } = {}) => {
    const mobile = isMobileViewport();
    const shouldOpen = mobile && open;
    shell.classList.toggle('mobile-nav-open', shouldOpen);
    menuButton.setAttribute('aria-expanded', String(shouldOpen));
    menuButton.setAttribute('aria-label', shouldOpen ? 'Close Fynvo navigation' : 'Open Fynvo navigation');
    sidebar.setAttribute('aria-hidden', String(mobile && !shouldOpen));

    if (shouldOpen) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      window.requestAnimationFrame(() => {
        const active = sidebar.querySelector('.nav-group button.active');
        (active || closeButton).focus({ preventScroll: true });
      });
    } else {
      document.body.style.overflow = previousOverflow;
      previousOverflow = '';
      if (restoreFocus && mobile && document.activeElement && sidebar.contains(document.activeElement)) {
        menuButton.focus({ preventScroll: true });
      }
    }
  };

  menuButton.addEventListener('click', () => setOpen(!shell.classList.contains('mobile-nav-open')));
  closeButton.addEventListener('click', () => setOpen(false));
  backdrop.addEventListener('click', () => setOpen(false));

  sidebar.addEventListener('click', (event) => {
    const destination = event.target.closest('.nav-group button');
    if (!destination || !isMobileViewport()) return;
    setOpen(false, { restoreFocus: false });
    window.requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: 'auto' }));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && shell.classList.contains('mobile-nav-open')) {
      event.preventDefault();
      setOpen(false);
    }
  });

  const media = window.matchMedia(MOBILE_QUERY);
  const syncBreakpoint = () => {
    setOpen(false, { restoreFocus: false });
    if (!media.matches) {
      sidebar.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = '';
    }
  };
  media.addEventListener?.('change', syncBreakpoint);
  syncBreakpoint();
}

const observer = new MutationObserver(() => ensureMobileNavigation());
observer.observe(document.documentElement, { childList: true, subtree: true });

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ensureMobileNavigation, { once: true });
} else {
  ensureMobileNavigation();
}

export { MOBILE_QUERY, RELEASE_VERSION };
