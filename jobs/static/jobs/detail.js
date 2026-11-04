(() => {
  const $ = s => document.querySelector(s);
  const inputs = [...document.querySelectorAll('[data-field]')];

  const pressureInput = $('#f-test_pressure');
  const pressureUnit = $('#f-test_pressure-unit');

  let originalPressureUnit = pressureUnit?.value || 'bar';
  let currentPressureUnit = originalPressureUnit;

  // Cal Date / Due Date: native calendar picker (ISO inside the input, dd/mm/yyyy in Excel)
  const calIn = $('#f-cal_date'), dueIn = $('#f-due_date');
  const dmyToIso = s => { const m = /^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/.exec((s || '').trim()); return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : ''; };
  const isoToDmy = s => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || ''); return m ? `${m[3]}/${m[2]}/${m[1]}` : ''; };
  const isDate = i => i === calIn || i === dueIn;
  const addMonths = (iso, n) => {                        // like Excel EDATE: 31 Aug + 18m -> 28 Feb
    const [y, m, d] = iso.split('-').map(Number);
    const last = new Date(y, m - 1 + n + 1, 0).getDate();
    const t = new Date(y, m - 1 + n, Math.min(d, last));
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
  };
  [calIn, dueIn].forEach(i => { if (i) i.value = dmyToIso(i.dataset.dmy); });

  const orig = {}; inputs.forEach(i => orig[i.name] = i.value);
  const bar = $('#savebar'), saveBtn = $('#save'), toastEl = $('#toast');
  const csrf = document.querySelector('meta[name=csrf]').content;
  const url = saveBtn.dataset.url;

  const dirty = () =>
  inputs.some(i => i.value !== orig[i.name]) ||
  (pressureUnit && pressureUnit.value !== originalPressureUnit);
  function refresh() {
    inputs.forEach(i => i.classList.toggle('dirty', i.value !== orig[i.name]));
    bar.classList.toggle('show', dirty());
  }
  inputs.forEach(i => i.addEventListener('input', refresh));

  if (pressureUnit) {
    pressureUnit.addEventListener('change', refresh);
  }
  if (calIn && dueIn) {
    const syncDue = () => { dueIn.value = calIn.value ? addMonths(calIn.value, 18) : ''; refresh(); };
    calIn.addEventListener('input', syncDue);
    calIn.addEventListener('change', syncDue);
  }

  function toast(msg, err) {
    toastEl.textContent = msg; toastEl.className = 'toast show' + (err ? ' err' : '');
    clearTimeout(toast.t); toast.t = setTimeout(() => toastEl.classList.remove('show'), err ? 5000 : 2500);
  }
  async function save() {
    if (!dirty()) return true;
    saveBtn.disabled = true; $('#savelbl').textContent = 'Saving…';
    try {
      const data = {};

      inputs.forEach(i => {
        if (i.name === 'test_pressure') {
          if (
            i.value !== orig[i.name] ||
            pressureUnit.value !== originalPressureUnit
          ) {
            data.test_pressure = i.value.trim()
              ? `${i.value.trim()} ${pressureUnit.value}`
              : '';
          }
        } else if (i.value !== orig[i.name]) {
          data[i.name] = isDate(i) ? isoToDmy(i.value) : i.value;
        }
      });
      const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify(data)});
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || 'Save failed');
      inputs.forEach(i => {
      const v = j.values[i.name] ?? '';

      if (i.name === 'test_pressure') {
        const match = v.match(
          /^(.*?)\s*(Kg\/cm\^2|MPa|psi|bar)$/i
        );

        if (match) {
          i.value = match[1].trim();
          pressureUnit.value = match[2];
        } else {
          i.value = v;
          pressureUnit.value = 'bar';
        }
      } else {
        i.value = isDate(i) ? dmyToIso(v) : v;
      }

      orig[i.name] = i.value;
    });

    currentPressureUnit = pressureUnit.value;
    originalPressureUnit = pressureUnit.value;
      refresh(); toast('Saved to Excel');
      if (j.url && !location.pathname.endsWith(j.url)) { location.replace(j.url); return false; }
      return true;
    } catch (e) { toast(e.message, true); return false; }
    finally { saveBtn.disabled = false; $('#savelbl').textContent = 'Save to Excel'; }
  }
  saveBtn.onclick = save;
  $('#discard').onclick = () => {
  inputs.forEach(i => i.value = orig[i.name]);

  if (pressureUnit) {
    pressureUnit.value = currentPressureUnit;
  }

  refresh();
};
  document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); save(); } });
  addEventListener('beforeunload', e => { if (dirty()) { e.preventDefault(); e.returnValue = ''; } });
  document.querySelectorAll('a[data-nav]').forEach(a => a.addEventListener('click', async e => {
    if (!dirty()) return; e.preventDefault(); if (await save()) location.href = a.href;
  }));

  const refSel = $('#f-hydro-ref');

  // printing: save pending edits first so documents match the Excel file
  document.querySelectorAll('[data-report]').forEach(b => b.addEventListener('click', async () => {
    const w = window.open('', '_blank');                       // open synchronously (popup-safe)
    if (!w) { toast('Allow pop-ups to print documents', true); return; }
    w.document.write('<p style="font:14px sans-serif;padding:24px">Preparing document…</p>');
    if (await save()) {
      const q = [];
      if (!b.hasAttribute('data-noprint')) q.push('print=1');
      if (b.hasAttribute('data-ref') && refSel && refSel.value) q.push('ref=' + encodeURIComponent(refSel.value));
      w.location.href = b.dataset.report + (q.length ? '?' + q.join('&') : '');
    } else w.close();
  }));
})();