// Fetches content.json (edited via /admin) and applies it to any element
// tagged with data-cms="key". Fails silently and keeps the hardcoded
// fallback text if content.json isn't reachable (e.g. opened as a local file).
(function () {
  const base = document.body.dataset.root || '.';
  fetch(base + '/content.json', { cache: 'no-store' })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data) return;
      document.querySelectorAll('[data-cms]').forEach(el => {
        const key = el.dataset.cms;
        if (!(key in data)) return;
        const value = data[key];
        const attr = el.dataset.cmsAttr;
        const prefix = el.dataset.cmsPrefix || '';
        if (attr) {
          el.setAttribute(attr, prefix + value);
        } else {
          el.innerHTML = value;
        }
      });
    })
    .catch(() => { /* keep fallback content */ });
})();
