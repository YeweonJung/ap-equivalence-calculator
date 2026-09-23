'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const labels = {patient:'피험자 ID',date:'처방일',drug:'성분·함량·제형이 적힌 약물명',product:'제품명 (선택)',daily:'하루 정/캡슐 수',days:'처방일수'};
  let generation = 0;
  $('rx-file').addEventListener('change', async () => {
    const token = ++generation;
    $('calculate').disabled = true; $('mapping').replaceChildren(); $('status').textContent = '';
    if (!$('rx-file').files[0]) return;
    $('inspection').textContent = '열 확인 중…';
    const form = new FormData(); form.append('file', $('rx-file').files[0]);
    try {
      const response = await fetch('/api/longitudinal/inspect', {method:'POST', body:form});
      const data = await response.json();
      if (token !== generation) return;
      if (!response.ok) throw new Error(data.error || '파일을 읽지 못했습니다.');
      for (const [field, label] of Object.entries(labels)) {
        const box = document.createElement('div'), title = document.createElement('label'), select = document.createElement('select');
        select.id = 'map-' + field; title.htmlFor = select.id; title.textContent = label; select.required = field !== 'product';
        select.add(new Option('열 선택', ''));
        data.columns.forEach(column => select.add(new Option(column, column)));
        select.value = data.mapping[field] || ''; box.append(title, select); $('mapping').append(box);
      }
      $('inspection').textContent = `${data.rows.toLocaleString()}행 · ${data.recognized ? '종단 처방 형식 인식 완료. 열 연결을 확인하세요.' : '자동 인식하지 못한 열을 직접 선택하세요.'}`;
      $('calculate').disabled = false;
    } catch (error) { if (token === generation) $('inspection').textContent = error.message; }
  });
  $('mode').addEventListener('change', () => {
    const common = $('mode').value === 'common', per = $('mode').value === 'per_patient';
    $('common').hidden = !common; $('per-patient').hidden = !per;
    $('reference-date').required = common; $('references').required = per;
  });
  $('longitudinal-form').addEventListener('submit', async event => {
    event.preventDefault();
    const mapping = Object.fromEntries(Object.keys(labels).map(k => [k, $('map-' + k).value]));
    const form = new FormData();
    form.append('file', $('rx-file').files[0]); form.append('mapping', JSON.stringify(mapping));
    form.append('mode', $('mode').value); form.append('policy', $('policy').value);
    form.append('reference_date', $('reference-date').value); form.append('ack', $('ack').checked ? 'yes' : '');
    if ($('mode').value === 'per_patient') form.append('references', $('references').files[0]);
    $('calculate').disabled = true; $('status').textContent = '처방기간과 용량을 검토하고 있습니다…';
    try {
      const response = await fetch('/api/longitudinal/analyze', {method:'POST', body:form});
      if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || '분석하지 못했습니다. 파일 크기와 입력을 확인하세요.'); }
      const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
      link.href = url; link.download = 'AP_equivalence_results.xlsx'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 60000);
      $('status').textContent = 'Excel을 받았습니다. Results는 환자별 결과, MedicationResults는 약물별 상세, Review는 확인할 항목입니다.';
    } catch (error) { $('status').textContent = error.message; }
    finally { $('calculate').disabled = false; }
  });
})();
