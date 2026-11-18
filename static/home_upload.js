'use strict';
(() => {
  const file = document.querySelector('#file'), name = document.querySelector('#file-name');
  const form = document.querySelector('#upload-form'), button = document.querySelector('#submit-button');
  const zone = document.querySelector('#drop-zone'), status = document.querySelector('#upload-status');
  let busy = false;
  const T = (key, ko) => (window.APi18n ? window.APi18n.t(key, ko) : ko);
  function selected() {if (file.files[0]) {name.removeAttribute('data-i18n');name.textContent = file.files[0].name;} else {name.setAttribute('data-i18n', 'choose');name.textContent = T('choose', 'Excel 또는 CSV 파일 선택');}status.textContent = '';status.dataset.error = 'false';}
  file.addEventListener('change', selected);
  ['dragenter','dragover'].forEach(event => zone.addEventListener(event, e => {e.preventDefault();if (!busy) zone.classList.add('dragging');}));
  ['dragleave','drop'].forEach(event => zone.addEventListener(event, e => {e.preventDefault();zone.classList.remove('dragging');}));
  zone.addEventListener('drop', e => {
    if (busy || !e.dataTransfer.files.length) return;
    if (e.dataTransfer.files.length > 1) {status.textContent = T('up_one', '한 번에 파일 하나를 선택해 주세요.');status.dataset.error = 'true';return;}
    file.files = e.dataTransfer.files;selected();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();if (busy || !file.files[0]) return;
    if (!/\.(csv|xlsx|xls)$/i.test(file.files[0].name)) {status.textContent=T('up_type', 'CSV 또는 Excel 파일을 선택해 주세요.');status.dataset.error='true';return;}
    const body = new FormData(form);
    busy = true;button.disabled = true;file.disabled = true;button.removeAttribute('data-i18n');button.textContent = T('up_busy', '파일을 분석하고 있습니다…');
    status.textContent = T('up_busy_status', '약물과 처방일을 확인하고 결과를 준비합니다.');status.dataset.error = 'false';
    try {
      const response = await fetch(form.action, {method:'POST', body});
      if (!response.ok) {
        if ([502, 503, 504].includes(response.status)) throw new Error(T('up_server', '서버에서 처리를 완료하지 못했습니다. 잠시 후 다시 계산해 주세요.'));
        const type = response.headers.get('Content-Type') || '';let message;
        if (type.includes('json')) message = (await response.json()).error;
        else {const page = new DOMParser().parseFromString(await response.text(), 'text/html');message = page.querySelector('.message, .error-message, main p, p')?.textContent;}
        throw new Error(message || T('up_fail', '파일을 처리하지 못했습니다. 열 이름과 파일 크기를 확인해 주세요.'));
      }
      const type = response.headers.get('Content-Type') || '';
      if (!type.includes('spreadsheetml')) throw new Error(T('up_nofile', '결과 파일을 받지 못했습니다. 입력 내용을 확인해 주세요.'));
      const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
      link.href = url;link.download = 'AP_equivalence_results.xlsx';
      document.body.append(link);link.click();link.remove();setTimeout(() => URL.revokeObjectURL(url), 60000);
      status.textContent = T('up_done', '계산 완료. 첫 시트(보완합계)에서 환자별 최종 합계를 확인하세요.');
    } catch (error) {status.textContent = error.message || T('up_conn', '연결을 확인한 뒤 다시 시도해 주세요.');status.dataset.error = 'true';}
    finally {busy = false;button.disabled = false;file.disabled = false;button.removeAttribute('data-i18n');button.textContent = T('up_again', '다시 계산하기 →');}
  });
})();
