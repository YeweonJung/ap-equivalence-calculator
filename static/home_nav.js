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
      // Research mode keeps the pre-redesign page: every calculator view, but not the home or help hub.
      section.hidden = view === 'all' ? ['home', 'help'].includes(section.dataset.view) : section.dataset.view !== view;
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

  // One base method for the whole page: the quick view has its own selector that mirrors #base-method.
  const base = document.querySelector('#base-method'), quickBase = document.querySelector('#base-method-quick');
  if (base && quickBase) {
    // Sync after every page script has run (the research bridge may lock #base-method to DDD).
    const sync = () => { quickBase.value = base.value; quickBase.disabled = base.disabled; };
    sync();
    document.addEventListener('DOMContentLoaded', sync);
    quickBase.addEventListener('change', () => {
      if (base.disabled) { sync(); return; }
      base.value = quickBase.value; base.dispatchEvent(new Event('change'));
    });
    base.addEventListener('change', () => { quickBase.value = base.value; });
  }

  // Home search box and example chips: open the one-line view and calculate.
  const runQuick = text => {
    const input = document.querySelector('#parser-input'), button = document.querySelector('#parse-button');
    if (!input || !button || !text.trim()) return;
    input.value = text.trim();
    input.dispatchEvent(new Event('input'));
    location.hash = '#quick';
    setTimeout(() => button.click(), 0);
  };
  document.querySelector('#home-quick-form')?.addEventListener('submit', event => {
    event.preventDefault();
    runQuick(document.querySelector('#home-quick-input').value);
  });
  document.querySelectorAll('.home-chips .chip').forEach(chip => chip.addEventListener('click', () => runQuick(chip.dataset.example)));
})();
