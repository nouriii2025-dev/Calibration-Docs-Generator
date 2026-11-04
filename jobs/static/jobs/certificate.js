/* Calibration certificate: average + deviation, calculated live from the measured readings. */
(function () {
  var tbl = document.getElementById('cal-results');
  if (!tbl) return;

  var STORE = 'cal-cert-readings:' + (tbl.dataset.ds || '');
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

  var CKSTORE = 'cal-cert-notes:' + (tbl.dataset.ds || '');
  var checks = Array.prototype.slice.call(document.querySelectorAll('input.ck'));

  function save() {
    try {
      localStorage.setItem(STORE, JSON.stringify(rows.map(function (tr) {
        var o = {};
        tr.querySelectorAll('.rd').forEach(function (i) { o[i.dataset.k] = i.value; });
        return o;
      })));
      var c = {};
      checks.forEach(function (i) { c[i.dataset.ck] = i.checked; });
      localStorage.setItem(CKSTORE, JSON.stringify(c));
    } catch (e) {}
  }

  function restore() {
    try {
      var data = JSON.parse(localStorage.getItem(STORE) || 'null');
      if (!data) return;
      rows.forEach(function (tr, i) {
        tr.querySelectorAll('.rd').forEach(function (inp) {
          if (data[i] && data[i][inp.dataset.k] != null) inp.value = data[i][inp.dataset.k];
        });
      });
    } catch (e) {}
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

  function restoreChecks() {
    try {
      var c = JSON.parse(localStorage.getItem(CKSTORE) || 'null');
      if (!c) return;
      checks.forEach(function (i) { if (c[i.dataset.ck] != null) i.checked = !!c[i.dataset.ck]; });
    } catch (e) {}
  }

  restore();
  tbl.querySelectorAll('.rd').forEach(padMeasured);
  restoreChecks();
  rows.forEach(calcRow);
  tbl.querySelectorAll('.rd').forEach(checkInput);
})();