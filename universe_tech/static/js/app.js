/* Site-wide behaviour. Kept in a file (not inline) so the Content-Security-Policy can forbid inline scripts. */
document.addEventListener('click', function (e) {
  var t = e.target.closest('[data-toggle-nav]');
  if (t) { document.getElementById('nav').classList.toggle('open'); return; }
  if (e.target.closest('[data-print]')) { window.print(); return; }
  var c = e.target.closest('[data-confirm]');
  if (c && !window.confirm(c.getAttribute('data-confirm'))) { e.preventDefault(); }
});
