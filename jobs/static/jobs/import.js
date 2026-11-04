(() => {
  const btn = document.getElementById('import-btn'), input = document.getElementById('import-file');
  if (!btn || !input) return;
  const csrf = document.querySelector('meta[name=csrf]').content;
  const toastEl = document.getElementById('toast');
  function toast(msg, err) {
    toastEl.textContent = msg; toastEl.className = 'toast show' + (err ? ' err' : '');
    clearTimeout(toast.t); toast.t = setTimeout(() => toastEl.classList.remove('show'), err ? 7000 : 4000);
  }
  btn.addEventListener('click', () => input.click());
  input.addEventListener('change', async () => {
    const file = input.files[0]; input.value = '';
    if (!file) return;
    if (!/\.xlsx$/i.test(file.name)) { toast('Please choose an .xlsx file.', true); return; }
    if (!confirm(`Import "${file.name}"?\n\nThe dashboard data will be replaced by this file. ` +
                 `A backup of the current data is saved first.`)) return;
    btn.disabled = true;
    const fd = new FormData(); fd.append('file', file);
    try {
      const r = await fetch(btn.dataset.url || '/import/', {method: 'POST', headers: {'X-CSRFToken': csrf}, body: fd});
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.ok) throw new Error(j.error || 'Import failed.');
      toast(`Imported ${j.rows} records: ${j.added} added, ${j.updated} updated, ${j.removed} removed.`);
      setTimeout(() => location.reload(), 1800);
    } catch (e) { toast(e.message, true); btn.disabled = false; }
  });
})();