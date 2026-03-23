export function initTabs() {
  const tabBar = document.getElementById('tabbar');
  if (!tabBar) return;

  function setTab(id) {
    const tabs = Array.from(tabBar.querySelectorAll('[data-tab]'));
    const panels = Array.from(document.querySelectorAll('[data-panel]'));
    tabs.forEach(t => {
      const active = t.getAttribute('data-tab') === id;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    panels.forEach(p => {
      const active = p.getAttribute('data-panel') === id;
      p.classList.toggle('hidden', !active);
    });
    try { window.dispatchEvent(new CustomEvent('bridge:tab', { detail: { tab: id } })); } catch (_) {}
  }

  tabBar.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-tab]');
    if (!btn) return;
    setTab(btn.getAttribute('data-tab'));
  });

  // Default: control-first
  setTab('control');
}

