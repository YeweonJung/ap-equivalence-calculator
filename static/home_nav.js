/* Home screen and separate views on one page, switched by the URL hash (#upload, #guide, #rules, #read, #quick).
   Research popups (?study_ai=...) skip the home screen and show every view, as before. */
(() => {
  'use strict';
  const views = Array.from(document.querySelectorAll('section.view[data-view]'));
  const tabs = document.querySelector('#tabs');
  if (!views.length) return;
  const study = new URLSearchParams(location.search).has('study_ai');
  const names = new Set(views.map(v => v.dataset.view));

  function show() {
    const wanted = location.hash.replace(/^#/, '');
    const view = study ? 'all' : (names.has(wanted) && wanted !== 'home' ? wanted : 'home');
    views.forEach(section => {
      section.hidden = view === 'all' ? section.dataset.view === 'home' : section.dataset.view !== view;
    });
    if (tabs) {
      tabs.hidden = view === 'home' || study;
      tabs.querySelectorAll('a[data-view]').forEach(link => {
        const group = ['guide', 'rules', 'read'].includes(view) ? 'help' : view;
        if (link.dataset.view === group) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
    }
    if (!study) window.scrollTo(0, 0);
    if (view === 'quick') document.querySelector('#parser-input')?.focus({preventScroll: true});
  }

  window.addEventListener('hashchange', show);
  show();
})();
