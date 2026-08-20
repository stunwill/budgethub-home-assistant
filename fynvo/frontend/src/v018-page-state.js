const INCOME_PAGE_CLASS = 'fynvo-income-page';

function syncPageState() {
  const heading = document.querySelector('.content > .header h1');
  const activeHeading = String(heading?.textContent || '').trim();
  document.body.classList.toggle(INCOME_PAGE_CLASS, activeHeading === 'Income');
}

const observer = new MutationObserver(syncPageState);

function startPageStateSync() {
  syncPageState();
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startPageStateSync, { once: true });
} else {
  startPageStateSync();
}
