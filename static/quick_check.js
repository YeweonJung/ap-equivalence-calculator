// 한 줄 확인 화면. 후보를 선택하기 전에는 약물명을 바꾸지 않습니다.
const parseButton = document.querySelector('#parse-button');
const parseInput = document.querySelector('#parser-input');
const parseOutput = document.querySelector('#parse-results');
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g,
  char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;'}[char]));
let currentText = '';
let currentItems = [];
let activeRequest = null;
const exportButton = document.querySelector('#export-quick');
const downloadStatus = document.querySelector('#download-status');
const formatDose = value => Number.isFinite(value) ? String(Number(value.toFixed(4))) : '—';

function itemHtml(item, index) {
  if (!item.ok) {
    const suggestions = (item.suggestions || []).map((candidate, candidateIndex) =>
      `<button type="button" class="suggestion-button" data-item="${index}" data-candidate="${candidateIndex}">${escapeHtml(candidate.alias)} (${escapeHtml(candidate.drug)})로 수정 · ${escapeHtml(candidate.distance)}글자 편집<br><small>${escapeHtml(candidate.explanation)}</small></button>`).join(' ');
    return `<div class="parse-item error"><b>${escapeHtml(item.original)}</b> — ${escapeHtml(item.error)}${suggestions ? `<div class="values">혹시 아래 약물인가요? 글자 차이는 약물의 동일성을 보장하지 않습니다. 이름을 확인하고 선택하세요. 용량·단위·빈도는 유지됩니다.</div><div class="suggestions">${suggestions}</div>` : ''}</div>`;
  }
  const values = `<table class="conversion-table"><caption>방법별 환산 결과 (mg/day)</caption><thead><tr><th>방법</th><th>결과 · 기준 약물</th></tr></thead><tbody>${item.conversions.map(value => {
    const reason = item.route === 'injection' && value.method !== 'DDD' && item.oral_equivalent_mg == null ? '단일 경구 대응량 없음' : '해당 방법의 계수 없음';
    return `<tr><th scope="row">${escapeHtml(value.method)}</th><td>${value.value == null ? `— (${reason})` : `${formatDose(value.value)} · ${escapeHtml(value.target)}${value.basis?.startsWith('경구') ? ' (경구 대응 추정)' : ''}`}</td></tr>`;
  }).join('')}</tbody></table>`;
  const steps = item.route === 'injection' && item.active_moiety_mg != null
    ? `입력 ${escapeHtml(item.input_dose_mg)} mg → 활성성분 ${escapeHtml(item.active_moiety_mg)} mg / ${escapeHtml(item.interval_days)}일 → 경구 대응 ${item.oral_equivalent_mg == null ? '단일값 없음' : escapeHtml(item.oral_equivalent_mg) + ' mg/day'}<br>` : '';
  return `<div class="parse-item"><div class="parse-top"><b>${escapeHtml(item.drug)}${item.daily_dose_mg == null ? '' : ` · ${formatDose(item.daily_dose_mg)} mg/day${item.route === 'injection' ? ' (평균 주사 성분량)' : ''}`}</b><span>${escapeHtml(item.status_message)}${item.needs_review ? ' · 검토 필요' : ''}</span></div><div class="values">${steps}${escapeHtml(item.warning)} ${escapeHtml(item.route === 'injection' ? item.formulation : '')}<br>${values}</div></div>`;
}

async function runQuickCheck() {
  if (location.protocol === 'file:') {
    parseOutput.textContent = '이 HTML 파일을 직접 열면 계산할 수 없습니다. Flask 앱을 실행한 주소에서 이용해 주세요.';
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
  parseOutput.textContent = '확인 중…';
  try {
    const response = await fetch(parseOutput.dataset.apiUrl, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: currentText}), signal: controller.signal
    });
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('계산 서버 응답을 확인할 수 없습니다. 앱 실행 주소와 서버 상태를 확인해 주세요.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '계산 요청을 처리하지 못했습니다.');
    if (activeRequest !== controller || parseInput.value.trim() !== currentText) return;
    currentItems = data.items;
    exportButton.hidden = false;
    parseOutput.innerHTML = data.items.map(itemHtml).join('');
    parseOutput.innerHTML += `<div class="parse-item"><b>입력 약물 합계 (환산법별)</b>${data.totals.map(total => {
      let result = '총합 계산 불가 (용량·단위·환산 지원 여부 확인)';
      if (total.total_equivalent_dose_mg !== null) result = `${escapeHtml(total.total_equivalent_dose_mg)} mg${total.needs_review ? ' · 검토 필요' : ''}`;
      else if (total.partial_equivalent_dose_mg !== null) result = `부분합 ${escapeHtml(total.partial_equivalent_dose_mg)} mg · 미환산 ${escapeHtml(total.unresolved_count)}건`;
      else if (total.status === 'non_target') result = '환산 대상 없음';
      return `<div class="values">${escapeHtml(total.method)} · ${escapeHtml(total.target_drug)}: ${result}</div>`;
    }).join('')}</div>`;
  } catch (error) {
    if (error.name !== 'AbortError' && activeRequest === controller) parseOutput.textContent = error.message || '분석하지 못했습니다.';
  } finally {
    if (activeRequest === controller) { parseButton.disabled = false; activeRequest = null; }
  }
}

parseButton.addEventListener('click', runQuickCheck);
parseInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing && !parseButton.disabled) runQuickCheck();
});
parseInput.addEventListener('input', () => {
  activeRequest?.abort();
  activeRequest = null;
  parseButton.disabled = false;
  exportButton.hidden = true;
  downloadStatus.textContent = '';
  currentItems = [];
  parseOutput.textContent = '';
});

exportButton.addEventListener('click', async () => {
  const text = currentText;
  if (!currentItems.length || parseInput.value.trim() !== text) return;
  exportButton.disabled = true;
  downloadStatus.textContent = 'Excel 생성 중…';
  try {
    const response = await fetch(exportButton.dataset.exportUrl, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})
    });
    if (!response.ok || !response.headers.get('content-type')?.includes('spreadsheetml')) throw new Error('Excel을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    const blob = await response.blob();
    if (parseInput.value.trim() !== text) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = 'AP_equivalence_quick_check.xlsx';
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadStatus.textContent = 'Excel 저장을 시작했습니다. 변환 근거와 검토표가 함께 포함됩니다.';
  } catch (error) {
    if (parseInput.value.trim() === text) downloadStatus.textContent = error.message;
  } finally { exportButton.disabled = false; }
});
parseOutput.addEventListener('click', event => {
  const selected = event.target.closest('.suggestion-button');
  if (!selected || parseButton.disabled || parseInput.value.trim() !== currentText) return;
  const item = currentItems[Number(selected.dataset.item)];
  const candidate = item?.suggestions?.[Number(selected.dataset.candidate)];
  if (!candidate) return;
  // Python의 문자 인덱스와 맞추어 이모지 등 UTF-16 두 칸 문자도 보존합니다.
  const characters = Array.from(currentText);
  parseInput.value = characters.slice(0, item.source_start).join('') + candidate.replacement + characters.slice(item.source_end).join('');
  runQuickCheck();
});
