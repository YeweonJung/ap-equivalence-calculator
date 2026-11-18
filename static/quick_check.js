// 등록된 약물만 계산하며, 미확인 이름은 사용자가 직접 수정합니다.
// Interface text goes through qcT; without static/i18n.js (tests, old pages) the Korean fallback is returned unchanged.
const qcT = (key, ko, vars) => {
  const i18n = globalThis.APi18n;
  if (i18n) return i18n.t(key, ko, vars);
  return vars ? String(ko).replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(vars, k) ? vars[k] : m)) : ko;
};
const parseButton = document.querySelector('#parse-button');
const parseInput = document.querySelector('#parser-input');
const parseOutput = document.querySelector('#parse-results');
const baseSelect = document.querySelector('#base-method');
const selectedBase = () => baseSelect?.value || 'ED95';
const supplementOrder = document.querySelector('#supplement-order');
function updateSupplementOrder() {
  if (!supplementOrder) return;
  const order = supplementOrder.dataset.priority.split(',').filter(method => method !== selectedBase());
  supplementOrder.textContent = order.join(' → ');
  // One-line summary under the upload box: base → first three supplements → unit.
  const strip = document.querySelector('#rule-strip');
  if (!strip) return;
  document.querySelector('#rule-base').textContent = selectedBase();
  document.querySelector('#rule-chain').textContent = order.slice(0, 3).join(' → ') + (order.length > 3 ? ' …' : '');
  document.querySelector('#rule-unit').textContent = JSON.parse(strip.dataset.units)[selectedBase()] || '';
}
updateSupplementOrder();
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g,
  char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;'}[char]));
let currentText = '';
let currentBase = 'ED95';
let currentItems = [];
let lastData = null;
let activeRequest = null;
const exportButton = document.querySelector('#export-quick');
const downloadStatus = document.querySelector('#download-status');
const formatDose = value => Number.isFinite(value) ? String(Number(value.toFixed(4))) : '—';

function feedbackHtml(item, index) {
  if (item.correction_suffix == null) return '';
  return `<details><summary>${qcT('qc_fix_sum', '약물명 직접 수정')}</summary><label>${qcT('qc_fix_label', '정확한 약물명')} <input id="correct-name-${index}" maxlength="60" autocomplete="off"></label><button type="button" class="manual-correction" data-item="${index}">${qcT('qc_fix_btn', '이 이름으로 다시 계산')}</button></details>` +
    (item.feedback_token ? `<label><input type="checkbox" id="feedback-consent-${index}">${qcT('qc_consent', '입력에 개인정보가 없고 약물명만 포함됨을 확인했으며, 수정한 이름 쌍을 약물명 추천 자동학습에 제공하는 데 동의합니다.')}</label><small>${qcT('qc_consent_note', '선택 사항 · 이 기록에는 용량·빈도·IP를 저장하지 않습니다. 수정 사례로 같은 오타의 추천을 개선하며, 약물 확정은 직접 선택해야 합니다. 기록은 180일간 보관합니다.')}</small>` : `<small>${qcT('qc_fb_off', '수정 기록 수집은 현재 사용할 수 없습니다. 이름 수정과 계산은 가능합니다.')}</small>`);
}

async function recordCorrection(item, index, alias, source) {
  if (!item.feedback_token || !document.querySelector(`#feedback-consent-${index}`)?.checked) return;
  const status = document.querySelector('#feedback-status');
  if (status) status.textContent = qcT('qc_fb_saving', '수정 기록 저장 중…');
  try {
    const response = await fetch('/api/name-feedback', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:item.feedback_token, selected_alias:alias, source, consent:true, learning_consent:true})});
    const data = await response.json();
    if (status) status.textContent = response.ok ? data.message : data.error;
  } catch (_) { if (status) status.textContent = qcT('qc_fb_fail', '기록을 저장하지 못했습니다. 계산에는 영향이 없습니다.'); }
}

function itemHtml(item, index) {
  if (!item.ok) {
    return `<div class="parse-item${item.review_required ? ' error' : ''}" data-review="${!!item.review_required}"><b>${escapeHtml(item.original)}</b> — <strong>${escapeHtml(item.status_label)}</strong><div class="values">${escapeHtml(item.error)}</div>${(item.learned_suggestions || []).map(c => `<div>${escapeHtml(item.suggestion_label || qcT('qc_suggest', '이전 수정 사례의 추천'))}: <button type="button" class="learned-correction" data-item="${index}" data-alias="${escapeHtml(c.alias)}">${qcT('qc_apply', '{alias} 확인 후 적용', {alias: escapeHtml(c.alias)})}</button></div>`).join('')}${feedbackHtml(item, index)}</div>`;
  }
  const values = `<table class="conversion-table"><caption>${qcT('qc_cap_methods', '방법별 환산 결과 (mg/day)')}</caption><thead><tr><th>${qcT('qc_th_method', '방법')}</th><th>${qcT('qc_th_result', '결과 · 기준 약물')}</th></tr></thead><tbody>${item.conversions.map(value => {
    const reason = item.route === 'injection' && value.method !== 'DDD' && item.oral_equivalent_mg == null ? qcT('qc_no_oral', '단일 경구 대응량 없음') : qcT('qc_no_factor', '해당 방법의 계수 없음');
    return `<tr><th scope="row">${escapeHtml(value.method)}</th><td>${value.value == null ? `— (${reason})` : `${formatDose(value.value)} · ${escapeHtml(value.target)}${value.basis?.startsWith('경구') ? qcT('qc_oral_est', ' (경구 대응 추정)') : ''}`}</td></tr>`;
  }).join('')}</tbody></table>`;
  const evidence = `<details><summary>${qcT('qc_ev_sum', '약물별 환산 근거 · 등급 평가 여부')}</summary><p>${qcT('qc_ev_note', '정식 GRADE 평가 미실시. 매칭 점수는 임상적 확률이 아닙니다.')}</p>${item.conversions.map(c => `<p><b>${escapeHtml(c.method)}</b> · ${escapeHtml(c.evidence?.calculation_basis || c.basis || '')}<br>${escapeHtml(c.evidence?.evidence_source || qcT('qc_ev_none', '계수 또는 적용 근거 없음'))}<br>${escapeHtml(c.evidence?.exclusion_conditions || '')}</p>`).join('')}<a href="/methods">${qcT('qc_ev_link', '근거와 적용 한계 보기')}</a></details>`;
  const steps = item.route === 'injection' && item.active_moiety_mg != null
    ? qcT('qc_steps', '입력 {a} mg → 활성성분 {b} mg / {c}일 → 경구 대응 {d}', {a: escapeHtml(item.input_dose_mg), b: escapeHtml(item.active_moiety_mg), c: escapeHtml(item.interval_days), d: item.oral_equivalent_mg == null ? qcT('qc_single_none', '단일값 없음') : escapeHtml(item.oral_equivalent_mg) + ' mg/day'}) + '<br>' : '';
  return `<div class="parse-item" data-review="${!!item.review_required}"><div class="parse-top"><b>${escapeHtml(item.drug)}${item.daily_dose_mg == null ? '' : ` · ${formatDose(item.daily_dose_mg)} mg/day${item.route === 'injection' ? qcT('qc_avg_inj', ' (평균 주사 성분량)') : ''}`}</b><span class="${item.review_required ? 'error-code' : ''}">${escapeHtml(item.status_code ? item.status_label : item.status_message)}</span></div><div class="values">${steps}${escapeHtml(item.warning)} ${escapeHtml(item.calculation_note || '')} ${escapeHtml(item.route === 'injection' ? item.formulation : '')}<br>${values}${evidence}</div></div>`;
}

function totalsHtml(totals, count) {
  return `<div class="parse-item quick-totals"><b>${qcT('qc_tot_head', '입력 약물 {n}개 · 방법별 합산', {n: count})}</b><p>${qcT('qc_tot_desc', '같은 방법·같은 기준 약물끼리 합산한 1일 환산량입니다.')}</p><table class="conversion-table"><caption>${qcT('qc_tot_cap', '전체 방법별 합산 결과 (mg/day)')}</caption><thead><tr><th>${qcT('qc_th_mt', '방법 · 기준 약물')}</th><th>${qcT('qc_th_sum', '합계 (mg/day)')}</th><th>${qcT('qc_th_check', '확인 사항')}</th></tr></thead><tbody>${totals.map(total => {
    const complete = total.total_equivalent_dose_mg != null;
    const result = complete ? formatDose(total.total_equivalent_dose_mg) : qcT('qc_na', '합산 불가');
    const notes = [];
    if (total.partial_equivalent_dose_mg != null) notes.push(qcT('qc_partial', '부분합 {v} mg/day', {v: formatDose(total.partial_equivalent_dose_mg)}));
    if (total.unresolved_count) notes.push(qcT('qc_unres', '미환산 {n}건', {n: total.unresolved_count}));
    if (total.excluded_count) notes.push(qcT('qc_excl', '환산 대상 외 {n}건 (0 기여)', {n: total.excluded_count}));
    if (total.review_required) notes.push(qcT('qc_xerr', 'x: 오류 · 검토필요'));
    return `<tr><th scope="row">${escapeHtml(total.method)} · ${escapeHtml(total.target_drug)}</th><td>${result}</td><td>${escapeHtml(notes.join(' · ') || qcT('qc_done', '합산 완료'))}</td></tr>`;
  }).join('')}</tbody></table><small>${qcT('qc_tot_small', '미환산 약물이 있는 방법은 전체 합계를 표시하지 않습니다. 아래에서 약물별 결과를 확인하세요.')}</small></div>`;
}

function scenariosHtml(cases, count) {
  const summary = `<div class="parse-item quick-scenarios"><b>${qcT('qc_sc_head', '입력 약물 {n}개 · 최종 합계', {n: count})}</b><p>${qcT('qc_sc_desc', '기준 {b}의 값을 유지하고, 계수가 없는 약물만 순차 보완합니다.', {b: escapeHtml(currentBase)})}</p><table class="conversion-table"><caption>${qcT('qc_sc_cap', '환산 결과 (mg/day)')}</caption><thead><tr><th>${qcT('qc_th_base', '기준 방법')}</th><th>${qcT('qc_th_total', '총합 · 기준약물')}</th><th>${qcT('qc_th_used', '사용 방법')}</th><th>${qcT('qc_th_comp', '보완 방법')}</th><th>${qcT('qc_th_status', '상태 · 확인 사항')}</th></tr></thead><tbody>${cases.map(scenario => {
    const total = scenario.total == null ? qcT('qc_na', '합산 불가') : `${formatDose(scenario.total)} mg/day`;
    const target = scenario.target == null ? '' : ` · ${escapeHtml(scenario.target)}`;
    const partial = scenario.partial == null ? '' : ' · ' + qcT('qc_partial', '부분합 {v} mg/day', {v: formatDose(scenario.partial)});
    const missing = scenario.missing ? ' · ' + qcT('qc_unres', '미환산 {n}건', {n: formatDose(scenario.missing)}) : '';
    const supplemented = scenario.supplemented ? ' · ' + qcT('qc_supp', '보완 {n}건', {n: formatDose(scenario.supplemented)}) : '';
    return `<tr><th scope="row">${escapeHtml(scenario.base)}</th><td>${total}${target}${partial}</td><td>${escapeHtml(scenario.methods)}</td><td>${escapeHtml(scenario.complement || qcT('qc_none', '없음'))}</td><td>${escapeHtml(scenario.status)}${missing}${supplemented}${scenario.status_code ? `<br>${escapeHtml(scenario.status_label)}` : ''}${scenario.note ? `<br><small>${escapeHtml(scenario.note)}</small>` : ''}</td></tr>`;
  }).join('')}</tbody></table></div>`;
  const details = cases.map(scenario => `<details class="scenario-details"><summary>${qcT('qc_det_sum', '{id} 약물별 근거', {id: escapeHtml(scenario.case_id)})}</summary><table class="conversion-table"><caption>${qcT('qc_det_cap', '{id} 약물별 환산 근거', {id: escapeHtml(scenario.case_id)})}</caption><thead><tr><th>${qcT('qc_th_drug', '약물')}</th><th>${qcT('qc_th_applied', '적용 방법')}</th><th>${qcT('qc_th_conv', '환산 결과')}</th><th>${qcT('qc_th_basis', '근거')}</th><th>${qcT('qc_th_src', '출처')}</th></tr></thead><tbody>${(scenario.details || []).map(detail => {
    const medication = detail.original == null || detail.original === detail.drug
      ? escapeHtml(detail.drug ?? detail.original)
      : `${escapeHtml(detail.original)} → ${escapeHtml(detail.drug)}`;
    const value = detail.value == null ? '—' : `${formatDose(detail.value)} mg/day${detail.target == null ? '' : ` · ${escapeHtml(detail.target)}`}`;
    const basis = detail.basis == null || detail.basis === '' ? '' : `<br>${escapeHtml(detail.basis)}`;
    return `<tr><th scope="row">${medication}</th><td>${escapeHtml(detail.actual || '—')}</td><td>${value}</td><td>${escapeHtml(detail.status)} ${escapeHtml(detail.reason)}${basis}${detail.note ? `<br>${escapeHtml(detail.note)}` : ''}</td><td>${escapeHtml(detail.source)}</td></tr>`;
  }).join('')}</tbody></table></details>`).join('');
  return summary + details;
}

async function runQuickCheck() {
  if (location.protocol === 'file:') {
    parseOutput.textContent = qcT('qc_file', '이 HTML 파일을 직접 열면 계산할 수 없습니다. Flask 앱을 실행한 주소에서 이용해 주세요.');
    return;
  }
  parseButton.disabled = true;
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  exportButton.hidden = true;
  downloadStatus.textContent = '';
  currentItems = [];
  currentText = parseInput.value.trim();
  currentBase = selectedBase();
  const base = currentBase;
  parseOutput.textContent = qcT('qc_checking', '확인 중…');
  try {
    const response = await fetch(parseOutput.dataset.apiUrl, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: currentText, base_method: base}), signal: controller.signal
    });
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error(qcT('qc_server', '계산 서버 응답을 확인할 수 없습니다. 앱 실행 주소와 서버 상태를 확인해 주세요.'));
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || qcT('qc_req_fail', '계산 요청을 처리하지 못했습니다.'));
    if (activeRequest !== controller || parseInput.value.trim() !== currentText || selectedBase() !== base) return;
    currentItems = data.items;
    exportButton.hidden = false;
    lastData = data;
    renderResult(data);
  } catch (error) {
    if (error.name !== 'AbortError' && activeRequest === controller) parseOutput.textContent = error.message || qcT('qc_fail', '분석하지 못했습니다.');
  } finally {
    if (activeRequest === controller) { parseButton.disabled = false; activeRequest = null; }
  }
}

function renderResult(data) {
    parseOutput.innerHTML = data.cases == null
      ? totalsHtml(data.totals, data.items.length) + data.items.map(itemHtml).join('')
      : scenariosHtml(data.cases, data.items.length)
        + data.items.map((item, index) => item.ok ? '' : itemHtml(item, index)).join('')
        + `<details class="original-totals"><summary>${qcT('qc_orig', '기존 방법별 결과')}</summary>${totalsHtml(data.totals, data.items.length)}${data.items.map((item, index) => item.ok ? itemHtml(item, index) : '').join('')}</details>`;
}
// Redraw the last result in the newly chosen language (server messages stay as returned).
globalThis.document?.addEventListener?.('ap:lang', () => { if (lastData && currentItems.length) renderResult(lastData); });

parseButton.addEventListener('click', runQuickCheck);
parseInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing && !parseButton.disabled) runQuickCheck();
});
function clearQuickResult() {
  activeRequest?.abort();
  activeRequest = null;
  parseButton.disabled = false;
  exportButton.hidden = true;
  downloadStatus.textContent = '';
  currentItems = [];
  lastData = null;
  parseOutput.textContent = '';
}
parseInput.addEventListener('input', clearQuickResult);
baseSelect?.addEventListener('change', () => { updateSupplementOrder(); clearQuickResult(); });

exportButton.addEventListener('click', async () => {
  const text = currentText;
  const base = currentBase;
  if (!currentItems.length || parseInput.value.trim() !== text || selectedBase() !== base) return;
  exportButton.disabled = true;
  downloadStatus.textContent = qcT('qc_xl_busy', 'Excel 생성 중…');
  try {
    const response = await fetch(exportButton.dataset.exportUrl, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text,base_method:base})
    });
    if (!response.ok || !response.headers.get('content-type')?.includes('spreadsheetml')) throw new Error(qcT('qc_xl_fail', 'Excel을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.'));
    const blob = await response.blob();
    if (parseInput.value.trim() !== text || selectedBase() !== base) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = 'AP_equivalence_quick_check.xlsx';
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadStatus.textContent = qcT('qc_xl_done', 'Excel 저장을 시작했습니다. 변환 근거와 검토표가 함께 포함됩니다.');
  } catch (error) {
    if (parseInput.value.trim() === text && selectedBase() === base) downloadStatus.textContent = error.message;
  } finally { exportButton.disabled = false; }
});
parseOutput.addEventListener('click', event => {
  if (parseButton.disabled || parseInput.value.trim() !== currentText) return;
  const manual = event.target.closest('.manual-correction, .learned-correction');
  if (!manual) return;
  const index = Number(manual.dataset.item);
  const item = currentItems[index];
  const alias = manual.dataset.alias || document.querySelector(`#correct-name-${index}`)?.value.trim();
  if (!item || !alias || !/^[a-zA-Z가-힣 -]{2,60}$/.test(alias)) return;
  recordCorrection(item, index, alias, manual.dataset.alias ? 'candidate' : 'manual');
  const characters = Array.from(currentText);
  parseInput.value = characters.slice(0,item.source_start).join('') + alias + item.correction_suffix + characters.slice(item.source_end).join('');
  runQuickCheck();
});
