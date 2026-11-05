/* Engineer name on reports: shows the default from settings, can be edited,
   and the edit is remembered per job + report type in this browser. */
(function () {
  var ds = (document.currentScript && document.currentScript.dataset.ds) || '';
  var inputs = Array.prototype.slice.call(document.querySelectorAll('input.sign-name'));

  function fit(i) { i.size = Math.max((i.value || '').length + 1, 8); }

  inputs.forEach(function (i) {
    if (i.dataset.sign === 'cert') return;     // certificate name is saved on the server by certificate.js
    var key = 'cal-sign:' + ds + ':' + i.dataset.sign;
    try {
      var saved = localStorage.getItem(key);
      if (saved !== null) i.value = saved;
    } catch (e) {}
    fit(i);
    i.addEventListener('input', function () {
      fit(i);
      try {
        if (i.value.trim() === '') localStorage.removeItem(key);
        else localStorage.setItem(key, i.value);
      } catch (e) {}
    });
    i.addEventListener('blur', function () {
      if (i.value.trim() === '') {
        i.value = i.defaultValue;
        fit(i);
      }
    });
  });
})();