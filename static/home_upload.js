'use strict';
(() => {
  const file = document.querySelector('#file'), name = document.querySelector('#file-name');
  const form = document.querySelector('#upload-form'), button = document.querySelector('#submit-button');
  const zone = document.querySelector('#drop-zone'), status = document.querySelector('#upload-status');
  let busy = false;
  function selected() {name.textContent = file.files[0]?.name || '파일을 선택하거나 여기에 놓으세요';status.textContent = '';status.dataset.error = 'false';}
  file.addEventListener('change', selected);
  ['dragenter','dragover'].forEach(event => zone.addEventListener(event, e => {e.preventDefault();if (!busy) zone.classList.add('dragging');}));
  ['dragleave','drop'].forEach(event => zone.addEventListener(event, e => {e.preventDefault();zone.classList.remove('dragging');}));
  zone.addEventListener('drop', e => {
    if (busy || !e.dataTransfer.files.length) return;
    if (e.dataTransfer.files.length > 1) {status.textContent = '한 번에 파일 하나를 선택해 주세요.';status.dataset.error = 'true';return;}
    file.files = e.dataTransfer.files;selected();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();if (busy || !file.files[0]) return;
    if (!/\.(csv|xlsx|xls)$/i.test(file.files[0].name)) {status.textContent='CSV 또는 Excel 파일을 선택해 주세요.';status.dataset.error='true';return;}
    const body = new FormData(form);
    busy = true;button.disabled = true;file.disabled = true;button.textContent = '파일을 분석하고 있습니다…';
    status.textContent = '약물과 처방일을 확인하고 결과를 준비합니다.';status.dataset.error = 'false';
    try {
      const response = await fetch(form.action, {method:'POST', body});
      if (!response.ok) {
        if ([502, 503, 504].includes(response.status)) throw new Error('서버에서 처리를 완료하지 못했습니다. 잠시 후 다시 계산해 주세요.');
        const type = response.headers.get('Content-Type') || '';let message;
        if (type.includes('json')) message = (await response.json()).error;
        else {const page = new DOMParser().parseFromString(await response.text(), 'text/html');message = page.querySelector('.message, .error-message, main p, p')?.textContent;}
        throw new Error(message || '파일을 처리하지 못했습니다. 열 이름과 파일 크기를 확인해 주세요.');
      }
      const type = response.headers.get('Content-Type') || '';
      if (!type.includes('spreadsheetml')) throw new Error('결과 파일을 받지 못했습니다. 입력 내용을 확인해 주세요.');
      const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
      link.href = url;link.download = 'AP_equivalence_results.xlsx';
      document.body.append(link);link.click();link.remove();setTimeout(() => URL.revokeObjectURL(url), 60000);
      status.textContent = '계산 완료. Excel의 Results에서 환자별 결과를 확인하세요.';
    } catch (error) {status.textContent = error.message || '연결을 확인한 뒤 다시 시도해 주세요.';status.dataset.error = 'true';}
    finally {busy = false;button.disabled = false;file.disabled = false;button.textContent = '다시 계산하기 →';}
  });
})();
