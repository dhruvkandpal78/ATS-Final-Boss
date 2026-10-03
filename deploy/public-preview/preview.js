(() => {
  'use strict';

  // The preview must never submit a form, even if markup is extended later.
  document.addEventListener('submit', event => {
    event.preventDefault();
    event.stopImmediatePropagation();
  }, true);

  const views = {
    '/': 'home-view',
    '/analyze': 'analyze-view',
    '/methodology': 'methodology-view',
    '/ownership': 'ownership-view'
  };

  function currentRoute() {
    const value = window.location.hash.slice(1);
    if (!value || value === '/') return { path: '/', anchor: '' };
    if (value.startsWith('/home/')) return { path: '/', anchor: value.slice(6) };
    if (value === '/lab') return { path: '/methodology', anchor: '' };
    return { path: views[value] ? value : '/', anchor: '' };
  }

  function renderRoute() {
    const route = currentRoute();
    for (const [path, id] of Object.entries(views)) {
      const view = document.getElementById(id);
      if (view) view.hidden = path !== route.path;
    }
    document.querySelectorAll('.site-nav [data-route]').forEach(link => {
      if (link.dataset.route === route.path) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    const menu = document.getElementById('site-nav');
    const toggle = document.getElementById('menu-toggle');
    if (menu) menu.classList.remove('open');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    if (route.anchor) {
      requestAnimationFrame(() => document.getElementById(route.anchor)?.scrollIntoView());
    } else {
      window.scrollTo(0, 0);
    }
  }

  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-route], a[data-home-anchor]');
    if (!link) return;
    event.preventDefault();
    const hash = link.dataset.homeAnchor
      ? `#/home/${encodeURIComponent(link.dataset.homeAnchor)}`
      : `#${link.dataset.route || '/'}`;
    if (window.location.hash === hash) renderRoute();
    else window.location.hash = hash;
  });
  window.addEventListener('hashchange', renderRoute);

  const themeButton = document.getElementById('theme-toggle');
  const themeSymbol = document.getElementById('theme-symbol');
  const themeLabel = document.getElementById('theme-label');
  function syncTheme() {
    const dark = document.documentElement.dataset.theme === 'dark';
    if (themeButton) {
      themeButton.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      themeButton.setAttribute('aria-pressed', String(dark));
    }
    if (themeSymbol) themeSymbol.textContent = dark ? '☀' : '☾';
    if (themeLabel) themeLabel.textContent = dark ? 'Light' : 'Dark';
  }
  syncTheme();
  themeButton?.addEventListener('click', () => {
    document.documentElement.dataset.theme =
      document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('atsfb-theme', document.documentElement.dataset.theme); } catch {}
    syncTheme();
  });

  const menu = document.getElementById('site-nav');
  const menuToggle = document.getElementById('menu-toggle');
  menuToggle?.addEventListener('click', () => {
    const open = menuToggle.getAttribute('aria-expanded') !== 'true';
    menuToggle.setAttribute('aria-expanded', String(open));
    menu?.classList.toggle('open', open);
  });
  window.addEventListener('scroll', () => {
    document.getElementById('site-header')?.classList.toggle('scrolled', window.scrollY > 24);
  }, { passive: true });

  let banner = document.getElementById('static-preview-banner');
  if (!banner) {
    banner = document.createElement('section');
    banner.id = 'static-preview-banner';
    banner.className = 'preview-banner';
    banner.setAttribute('role', 'status');
    const heading = document.createElement('strong');
    heading.textContent = 'Static website preview';
    const detail = document.createElement('span');
    detail.textContent = 'This free-hosted preview does not analyze documents. Do not enter or upload personal information.';
    banner.append(heading, detail);
    document.body.insertBefore(banner, document.body.firstChild);
  }

  const analysis = document.getElementById('analyze-view');
  if (analysis) {
    const notice = document.createElement('section');
    notice.className = 'panel preview-notice';
    notice.setAttribute('aria-labelledby', 'preview-notice-title');
    notice.innerHTML = '<span class="eyebrow">Preview only</span><h2 id="preview-notice-title">Analysis is unavailable on this static site.</h2><p>The page is provided to preview the interface. There is no analysis backend, and no document is uploaded or processed here.</p>';
    const insertionPoint = analysis.querySelector('.page-heading') || analysis.querySelector('.wrap');
    if (insertionPoint) insertionPoint.after(notice);
    analysis.querySelectorAll('input, textarea, select, .drop-zone, .file-row, .form-actions, .processing, #results').forEach(control => {
      if ('disabled' in control) control.disabled = true;
      else control.setAttribute('aria-disabled', 'true');
      if (control.matches('#results, .processing')) control.hidden = true;
    });
    analysis.querySelectorAll('.input-panel, .guidance-panel').forEach(panel => { panel.hidden = true; });
    analysis.querySelectorAll('button').forEach(button => { button.disabled = true; });
  }
  renderRoute();
})();
