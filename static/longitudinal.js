'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const T = (key, ko) => (window.APi18n ? window.APi18n.t(key, ko) : ko);
  const labels = {patient:'피험자 ID',date:'처방일',drug:'성분·함량·제형이 적힌 약물명',product:'제품명 (선택)',code:'보험 약품코드 (선택)',daily:'하루 정/캡슐 수',days:'처방일수 (선택)'};
  const fieldLabel = field => T('lf_' + field, labels[field]);
  let generation = 0, lastInspect = null, lastStatus = null;
  const inspectText = d => T('lj_rows', '{n}행 · ').replace('{n}', d.rows.toLocaleString()) + (d.recognized ? T('lj_recog', '열 이름이 같은 칸은 미리 채웠습니다. 칸마다 맞는 열인지 확인하세요.') : T('lj_unrecog', '빈 칸에 맞는 열을 고르세요. 열 이름이 같은 칸은 미리 채웠습니다.'));
  document.addEventListener('ap:lang', () => {
    for (const field of Object.keys(labels)) { const title = document.querySelector(`label[for="map-${field}"]`); if (title) title.textContent = fieldLabel(field); }
    const empty = document.querySelectorAll('#mapping option[value=""]'); empty.forEach(o => { o.textContent = lastInspect ? T('lj_col', '열 선택') : T('lj_wait', '파일을 먼저 고르세요'); });
    if (lastInspect) $('inspection').textContent = inspectText(lastInspect);
    if (lastStatus) $('status').textContent = T(lastStatus[0], lastStatus[1]);
  });
  // The boxes are on the page from the start; they list the file's columns once a file is chosen.
  function build(columns, mapping) {
    $('mapping').replaceChildren();
    for (const field of Object.keys(labels)) {
      const box = document.createElement('div'), title = document.createElement('label'), select = document.createElement('select');
      select.id = 'map-' + field; title.htmlFor = select.id; title.textContent = fieldLabel(field); select.required = !['product', 'days', 'code'].includes(field);
      select.add(new Option(columns.length ? T('lj_col', '열 선택') : T('lj_wait', '파일을 먼저 고르세요'), ''));
      columns.forEach(column => select.add(new Option(column, column)));
      select.disabled = !columns.length; select.value = mapping[field] || ''; box.append(title, select); $('mapping').append(box);
    }
  }
  build([], {});
  $('rx-file').addEventListener('change', async () => {
    const token = ++generation;
    $('calculate').disabled = true; build([], {}); $('status').textContent = ''; lastInspect = null; lastStatus = null;
    $('inspection').removeAttribute('data-i18n');
    if (!$('rx-file').files[0]) { $('inspection').textContent = T('lp_inspect', $('inspection').textContent); return; }
    $('inspection').textContent = T('lj_checking', '열 확인 중…');
    const form = new FormData(); form.append('file', $('rx-file').files[0]);
    try {
      const response = await fetch('/api/longitudinal/inspect', {method:'POST', body:form});
      const data = await response.json();
      if (token !== generation) return;
      if (!response.ok) throw new Error(data.error || T('lj_read_fail', '파일을 읽지 못했습니다.'));
      build(data.columns, data.mapping);
      lastInspect = data; $('inspection').textContent = inspectText(data);
      $('calculate').disabled = false;
    } catch (error) { if (token === generation) $('inspection').textContent = error.message; }
  });
  $('longitudinal-form').addEventListener('submit', async event => {
    event.preventDefault();
    const mapping = Object.fromEntries(Object.keys(labels).map(k => [k, $('map-' + k).value]));
    const form = new FormData();
    form.append('file', $('rx-file').files[0]); form.append('mapping', JSON.stringify(mapping));
    form.append('mode', 'all_dates'); form.append('base_method', $('lg-base') ? $('lg-base').value : 'ED95'); form.append('ack', $('ack').checked ? 'yes' : '');
    $('calculate').disabled = true; $('status').textContent = T('lj_calc', '환자·처방일별 용량을 계산하고 있습니다…');
    try {
      const response = await fetch('/api/longitudinal/analyze', {method:'POST', body:form});
      if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || T('lj_fail', '분석하지 못했습니다. 파일 크기와 입력을 확인하세요.')); }
      const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
      link.href = url; link.download = 'AP_equivalence_results.xlsx'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 60000);
      lastStatus = ['lj_done', 'Excel을 받았습니다. Results는 환자·처방일별 결과, MedicationResults는 약물별 상세, Review는 확인할 항목입니다.']; $('status').textContent = T(...lastStatus);
    } catch (error) { $('status').textContent = error.message; }
    finally { $('calculate').disabled = false; }
  });
})();
