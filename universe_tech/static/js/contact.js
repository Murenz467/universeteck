(function () {
  var phone = document.currentScript.getAttribute('data-phone');
  var form = document.getElementById('wa-form');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = document.getElementById('wa-name'), msg = document.getElementById('wa-msg');
    if (!name.value.trim() || !msg.value.trim()) { (name.value.trim() ? msg : name).focus(); return; }
    var text = 'Hello Universe Tech, my name is ' + name.value.trim() + '.\n' +
               'I need: ' + document.getElementById('wa-svc').value + '.\n\n' + msg.value.trim();
    window.open('https://wa.me/' + phone + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
  });
})();
