// Brief signup forms: POST to the signup worker (Brevo double opt-in). Works without JS too (plain form POST + redirect).
(function () {
  function msg(f, text, ok) {
    var m = f.parentNode.querySelector('.sub-msg'); if (!m) { m = document.createElement('p'); m.className = 'sub-msg'; m.setAttribute('role', 'status'); f.parentNode.appendChild(m); }
    m.textContent = text; m.className = 'sub-msg ' + (ok ? 'ok' : 'err');
  }
  document.querySelectorAll('form.sub-form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var b = f.querySelector('button'); b.disabled = true;
      fetch(f.action, { method: 'POST', body: new FormData(f), headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json().catch(function () { return { ok: false, message: 'Something went wrong. Please try again.' }; }); })
        .then(function (d) { msg(f, d.message || (d.ok ? 'Check your email to confirm.' : 'Something went wrong.'), d.ok); if (d.ok) f.reset(); })
        .catch(function () { msg(f, 'Could not reach the signup service. Please try again.', false); })
        .then(function () { b.disabled = false; });
    });
  });
  var s = (location.search.match(/[?&]status=([\w-]+)/) || [])[1], box = document.getElementById('sub-status');
  if (box && s) {
    var t = { 'check-email': 'Almost done! Check your email and click the confirmation link.', confirmed: "You're confirmed. Welcome to the Brief! Watch for the next issue.", error: 'Something went wrong. Please try again.' }[s];
    if (t) { box.textContent = t; box.className = 'sub-msg ' + (s === 'error' ? 'err' : 'ok'); box.hidden = false; }
  }
})();
