// 한 줄 확인 화면. 후보를 선택하기 전에는 약물명을 바꾸지 않습니다.
const parseButton = document.querySelector('#parse-button');
const parseInput = document.querySelector('#parser-input');
const parseOutput = document.querySelector('#parse-results');
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g,
  char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;'}[char]));
let currentText = '';
let currentItems = [];

function itemHtml(item, index) {
  if (!item.ok) {
    const suggestions = (item.suggestions || []).map((candidate, candidateIndex) =>
      `<button type="button" class="suggestion-button" data-item="${index}" data-candidate="${candidateIndex}">${escapeHtml(candidate.alias)} (${escapeHtml(candidate.drug)})로 수정</button>`).join(' ');
    return `<div class="parse-item error"><b>${escapeHtml(item.original)}</b> — ${escapeHtml(item.error)}${suggestions ? `<div class="values">혹시 아래 약물인가요? 이름을 확인하고 선택하세요. 용량·단위·빈도는 유지됩니다.</div><div class="suggestions">${suggestions}</div>` : ''}</div>`;
  }
  const values = item.conversions.filter(value => value.value !== null).map(value =>
    `<b>${escapeHtml(value.method)}</b> ${escapeHtml(value.value)} mg (${escapeHtml(value.target)})${value.basis?.startsWith('경구') ? ' (경구 대응 추정)' : ''}`).join(' · ');
  const steps = item.route === 'injection' && item.active_moiety_mg != null
    ? `입력 ${escapeHtml(item.input_dose_mg)} mg → 활성성분 ${escapeHtml(item.active_moiety_mg)} mg / ${escapeHtml(item.interval_days)}일 → 경구 대응 ${item.oral_equivalent_mg == null ? '단일값 없음' : escapeHtml(item.oral_equivalent_mg) + ' mg/day'}<br>` : '';
  return `<div class="parse-item"><div class="parse-top"><b>${escapeHtml(item.drug)}${item.daily_dose_mg == null ? '' : ` · ${escapeHtml(item.daily_dose_mg)} mg/day${item.route === 'injection' ? ' (평균 주사 성분량)' : ''}`}</b><span>${escapeHtml(item.status_message)}${item.needs_review ? ' · 검토 필요' : ''}</span></div><div class="values">${steps}${escapeHtml(item.warning)} ${escapeHtml(item.route === 'injection' ? item.formulation : '')}<br>${values}</div></div>`;
}

async function runQuickCheck() {
  if (location.protocol === 'file:') {
    parseOutput.textContent = '이 HTML 파일을 직접 열면 계산할 수 없습니다. Flask 앱을 실행한 주소에서 이용해 주세요.';
    return;
  }
  parseButton.disabled = true;
  currentItems = [];
  currentText = parseInput.value.trim();
  parseOutput.textContent = '확인 중…';
  try {
    const response = await fetch(parseOutput.dataset.apiUrl, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: currentText})
    });
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('계산 서버 응답을 확인할 수 없습니다. 앱 실행 주소와 서버 상태를 확인해 주세요.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '계산 요청을 처리하지 못했습니다.');
    if (parseInput.value.trim() !== currentText) return;
    currentItems = data.items;
    parseOutput.innerHTML = data.items.map(itemHtml).join('');
    parseOutput.innerHTML += `<div class="parse-item"><b>입력 약물 합계 (환산법별)</b>${data.totals.map(total => {
      let result = '총합 계산 불가 (용량·단위·환산 지원 여부 확인)';
      if (total.total_equivalent_dose_mg !== null) result = `${escapeHtml(total.total_equivalent_dose_mg)} mg${total.needs_review ? ' · 검토 필요' : ''}`;
      else if (total.partial_equivalent_dose_mg !== null) result = `부분합 ${escapeHtml(total.partial_equivalent_dose_mg)} mg · 미환산 ${escapeHtml(total.unresolved_count)}건`;
      else if (total.status === 'non_target') result = '환산 대상 없음';
      return `<div class="values">${escapeHtml(total.method)} · ${escapeHtml(total.target_drug)}: ${result}</div>`;
    }).join('')}</div>`;
  } catch (error) {
    parseOutput.textContent = error.message || '분석하지 못했습니다.';
  } finally {
    parseButton.disabled = false;
  }
}

parseButton.addEventListener('click', runQuickCheck);
parseInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing && !parseButton.disabled) runQuickCheck();
});
parseInput.addEventListener('input', () => {
  currentItems = [];
  parseOutput.textContent = '';
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
