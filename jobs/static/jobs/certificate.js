/* Calibration certificate: average + deviation, calculated live from the measured readings. */
(function () {
  var tbl = document.getElementById('cal-results');
  if (!tbl) return;

    /* Everything typed here is saved on the server (data/certificates), so it survives Excel imports.
     localStorage keys are only read once, to carry over readings typed before this change. */
  var DS = tbl.dataset.ds || '';
  var OLD_READINGS = 'cal-cert-readings:' + DS, OLD_NOTES = 'cal-cert-notes:' + DS, OLD_SIGN = 'cal-sign:' + DS + ':cert';
  var SAVE_URL = (document.currentScript && document.currentScript.dataset.saveUrl) || '';
  var csrfMeta = document.querySelector('meta[name=csrf]');
  var CSRF = csrfMeta ? csrfMeta.content : '';
  var state = {};
  try { state = JSON.parse(document.getElementById('cert-state').textContent) || {}; } catch (e) {}
  function lsGet(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function lsRaw(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  var DP = { avg_u: +(tbl.dataset.dpAvg || 3), avg_m: 5, dev_u: +(tbl.dataset.dpDev || 3), dev_m: 5 };
  var rows = Array.prototype.slice.call(tbl.querySelectorAll('tbody tr'));
  var DP_MEAS = tbl.dataset.dpMeas === undefined || tbl.dataset.dpMeas === '' ? null : +tbl.dataset.dpMeas;

  function num(v) {
    var n = parseFloat(v);
    return isFinite(n) ? n : null;
  }
  function fmt(v, d) {
    var r = Number(v.toFixed(d));
    return (Object.is(r, -0) ? 0 : r).toFixed(d);
  }
  function padMeasured(inp) {
    if (DP_MEAS === null) return;
    var k = inp.dataset.k;
    if (k !== 'up_u' && k !== 'dn_u') return;       // mA readings are left as typed
    var v = num(inp.value);
    if (v !== null) inp.value = fmt(v, DP_MEAS);
  }
  function out(tr, key, v) {
    var el = tr.querySelector('[data-o="' + key + '"]');
    if (!el) return;                       // column not present (FF layout has no mA)
    el.textContent = v === null ? '' : fmt(v, DP[key]);
  }
  function rd(tr, key) {
    var el = tr.querySelector('[data-k="' + key + '"]');
    return el ? num(el.value) : null;
  }

  tbl.addEventListener('input', function (e) {
    var tr = e.target.closest('tr');
    if (tr && e.target.classList.contains('rd')) { checkInput(e.target); calcRow(tr); save(); }
  });

  function calcRow(tr) {
    var applied = num(tr.dataset.applied);
    var equiv = num(tr.dataset.equiv);
    var upU = rd(tr, 'up_u'), dnU = rd(tr, 'dn_u');
    var upM = rd(tr, 'up_m'), dnM = rd(tr, 'dn_m');

    var avgU = (upU !== null && dnU !== null) ? (upU + dnU) / 2 : null;
    var avgM = (upM !== null && dnM !== null) ? (upM + dnM) / 2 : null;

    out(tr, 'avg_u', avgU);
    out(tr, 'avg_m', avgM);
    out(tr, 'dev_u', avgU !== null && applied !== null ? avgU - applied : null);
    out(tr, 'dev_m', avgM !== null && equiv !== null ? avgM - equiv : null);
  }

    /* mbar readings must be within applied +/- (accuracy x upper range); otherwise the box turns red */
    /* Readings must stay within tolerance of the applied / equivalent value, otherwise the box turns red.
     mbar columns: applied +/- (accuracy x upper range)
     mA columns:   equivalent mA +/- ((accuracy x upper range) x 16) / upper range */
  var TOL = num(tbl.dataset.tol);
  var TOL_MA = num(tbl.dataset.tolMa);
  function checkInput(inp) {
    var k = inp.dataset.k, tr = inp.closest('tr'), tol, target, dp;
    if (k === 'up_u' || k === 'dn_u') { tol = TOL; target = num(tr.dataset.applied); dp = DP_MEAS === null ? 4 : DP_MEAS; }
    else if (k === 'up_m' || k === 'dn_m') { tol = TOL_MA; target = num(tr.dataset.equiv); dp = 4; }
    else return;
    var v = num(inp.value);
    var bad = tol !== null && target !== null && v !== null && Math.abs(v - target) > tol + 1e-9;
    inp.classList.toggle('bad', bad);
    inp.title = bad ? 'Out of tolerance: allowed ' + fmt(target - tol, dp) + ' to ' + fmt(target + tol, dp) : '';
  }

    var checks = Array.prototype.slice.call(document.querySelectorAll('input.ck'));
  var signIn = document.querySelector('input.sign-name[data-sign="cert"]');
  var statusEl = document.getElementById('cert-status');

  function setStatus(msg, err) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = 'cert-status' + (err ? ' err' : '');
  }

  function snapshot() {
    var o = {
      readings: rows.map(function (tr) {
        var r = {};
        tr.querySelectorAll('.rd').forEach(function (i) { r[i.dataset.k] = i.value; });
        return r;
      }),
      calc: rows.map(function (tr) {
        var r = {};
        tr.querySelectorAll('[data-o]').forEach(function (c) { r[c.dataset.o] = c.textContent; });
        return r;
      }),
      checks: {}
    };
    checks.forEach(function (i) { o.checks[i.dataset.ck] = i.checked; });
    if (signIn) o.sign = { cert: signIn.value };
    return o;
  }

  /* autosave: short debounce, one request at a time, flushed when the page is closed */
  var timer = null, inflight = false, pending = false;
  function save() {
    pending = true;
    setStatus('Saving…');
    clearTimeout(timer);
    timer = setTimeout(flush, 400);
  }
  function flush() {
    clearTimeout(timer); timer = null;
    if (!pending || inflight || !SAVE_URL) return;
    pending = false; inflight = true;
    fetch(SAVE_URL, {
      method: 'POST', keepalive: true,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(snapshot())
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j.ok) throw new Error(j.error || 'Save failed');
      inflight = false;
      if (pending) flush(); else setStatus('All changes saved');
    }).catch(function (e) {
      inflight = false; pending = true;
      setStatus('Not saved – ' + (e.message || 'check the connection'), true);
    });
  }
  addEventListener('pagehide', function () { if (pending) flush(); });

  function restore() {
    var data = state.readings || null;
    var migrated = false;
    if (!data) { data = lsGet(OLD_READINGS); migrated = !!data; }     // one-time carry-over
    if (data) {
      rows.forEach(function (tr, i) {
        tr.querySelectorAll('.rd').forEach(function (inp) {
          if (data[i] && data[i][inp.dataset.k] != null) inp.value = data[i][inp.dataset.k];
        });
      });
    }
    return migrated;
  }

  function restoreChecks() {
    var c = state.checks || null, migrated = false;
    if (!c) { c = lsGet(OLD_NOTES); migrated = !!c; }
    if (c) checks.forEach(function (i) { if (c[i.dataset.ck] != null) i.checked = !!c[i.dataset.ck]; });
    return migrated;
  }

  function fitSign() { if (signIn) signIn.size = Math.max((signIn.value || '').length + 1, 8); }
  function restoreSign() {
    if (!signIn) return false;
    var v = (state.sign && state.sign.cert) || null, migrated = false;
    if (!v) { v = lsRaw(OLD_SIGN); migrated = !!v; }
    if (v) signIn.value = v;
    fitSign();
    signIn.addEventListener('input', function () { fitSign(); save(); });
    signIn.addEventListener('blur', function () {
      if (signIn.value.trim() === '') { signIn.value = signIn.defaultValue; fitSign(); save(); }
    });
    return migrated;
  }

  tbl.addEventListener('input', function (e) {
    var tr = e.target.closest('tr');
    if (tr && e.target.classList.contains('rd')) { calcRow(tr); save(); }
  });

  tbl.addEventListener('change', function (e) {
    var tr = e.target.closest('tr');
    if (tr && e.target.classList.contains('rd')) { padMeasured(e.target); checkInput(e.target); calcRow(tr); save(); }
  });
  checks.forEach(function (i) { i.addEventListener('change', save); });

  var migrated = restore();
  tbl.querySelectorAll('.rd').forEach(padMeasured);
  migrated = restoreChecks() || migrated;
  migrated = restoreSign() || migrated;
  rows.forEach(calcRow);
  tbl.querySelectorAll('.rd').forEach(checkInput);

  /* first load after this change, or calculated values out of step with the saved ones: save them now */
  var firstSave = migrated || !state.calc || JSON.stringify(snapshot().calc) !== JSON.stringify(state.calc);
  if (firstSave && (migrated || state.readings)) save(); else setStatus(state.readings ? 'All changes saved' : '');

  /* Refresh from Excel: explicit, per certificate */
  var refreshBtn = document.getElementById('cert-refresh');
  if (refreshBtn) refreshBtn.addEventListener('click', function () {
    if (!confirm('Refresh this certificate with the latest Excel data?\n\n' +
                 'Customer, instrument, range, dates and other job details are replaced with the Excel values. ' +
                 'Your readings, ticked notes and engineer name are kept.')) return;
    refreshBtn.disabled = true;
    flush();
    fetch(refreshBtn.dataset.url, { method: 'POST', headers: { 'X-CSRFToken': CSRF } })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error(j.error || 'Refresh failed');
        if (j.range_changed) alert('The Cal. Range changed, so the applied values changed. Please re-check the readings.');
        location.reload();
      })
      .catch(function (e) { refreshBtn.disabled = false; setStatus(e.message, true); });
  });
})();