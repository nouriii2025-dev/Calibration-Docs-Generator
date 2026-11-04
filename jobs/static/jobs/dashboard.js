(() => {
  const $ = s => document.querySelector(s);
  const body = $('#rows'), q = $('#q'), fEq = $('#f-eq'), fSt = $('#f-st'), fDt = $('#f-dt'), fSn = $('#f-sn');
  const rows = [...body.querySelectorAll('tr')];
  const PAGE = 25; let page = 1, sortKey = null, sortDir = 1, view = rows.slice();

  const go = tr => location.href = tr.dataset.href;
  rows.forEach(tr => {
    tr.tabIndex = 0;
    tr.addEventListener('click', () => go(tr));
    tr.addEventListener('keydown', e => { if (e.key === 'Enter') go(tr); });
  });

  function apply() {
    const terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    view = rows.filter(tr => {
      const d = tr.dataset;
      if (fEq.value && d.eq !== fEq.value) return false;
      if (fSt.value && d.st !== fSt.value) return false;
      if (fDt.value && d.dt !== fDt.value) return false;
      if (fSn.value === 'has' && !d.sn) return false;
      if (fSn.value === 'missing' && d.sn) return false;
      return terms.every(t => d.search.includes(t));
    });
    if (sortKey) view.sort((a, b) => sortDir * a.cells[sortKey].textContent.trim().localeCompare(b.cells[sortKey].textContent.trim(), undefined, {numeric: true}));
    page = 1; render();
  }
  function render() {
    const pages = Math.max(1, Math.ceil(view.length / PAGE));
    page = Math.min(page, pages);
    const slice = new Set(view.slice((page - 1) * PAGE, page * PAGE));
    rows.forEach(tr => tr.hidden = !slice.has(tr));
    view.forEach(tr => body.appendChild(tr));            // keep sort order in DOM
    $('#count').textContent = `${view.length} of ${rows.length} records`;
    $('#pinfo').textContent = `Page ${page} / ${pages}`;
    $('#prev').disabled = page <= 1; $('#next').disabled = page >= pages;
    $('#empty').style.display = view.length ? 'none' : 'block';
    const hl = q.value.trim();
    $('#reset').hidden = !(hl || fEq.value || fSt.value || fDt.value || fSn.value);
  }
  let t; q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(apply, 120); });
  [fEq, fSt, fDt, fSn].forEach(s => s.addEventListener('change', apply));
  $('#prev').onclick = () => { page--; render(); $('.tablewrap').scrollTop = 0; };
  $('#next').onclick = () => { page++; render(); $('.tablewrap').scrollTop = 0; };
  $('#reset').onclick = () => { q.value = ''; [fEq, fSt, fDt, fSn].forEach(s => s.value = ''); apply(); };
  document.querySelectorAll('thead th').forEach((th, idx) => th.addEventListener('click', () => {
    sortDir = sortKey === idx ? -sortDir : 1; sortKey = idx;
    document.querySelectorAll('th').forEach(h => { h.classList.remove('sorted'); h.querySelector('.ar').textContent = ''; });
    th.classList.add('sorted'); th.querySelector('.ar').textContent = sortDir > 0 ? '↑' : '↓';
    apply();
  }));
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.blur(); }
  });
  // restore state when coming back from a record
  try { const s = JSON.parse(sessionStorage.getItem('calq') || '{}'); if (s.q) q.value = s.q; if (s.eq) fEq.value = s.eq; } catch (e) {}
  addEventListener('pagehide', () => { try { sessionStorage.setItem('calq', JSON.stringify({q: q.value, eq: fEq.value})); } catch (e) {} });
  apply();
})();
