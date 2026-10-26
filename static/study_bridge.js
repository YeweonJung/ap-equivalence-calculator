/* Research popup bridge: only condition metadata is sent to the study opener. */
(() => {
  const params = new URLSearchParams(location.search);
  const mode = params.get('study_ai');
  const origin = params.get('study_origin');
  const trial = params.get('study_trial');
  const nonce = params.get('study_nonce');
  const origins = new Set(['https://ap-dose-validation.yewonjeong000.chatgpt.site',
    'http://localhost:8088', 'http://127.0.0.1:8088']);
  if (!['off','qwen','gemma','nemotron','xing','lfm'].includes(mode) || !origins.has(origin) || !trial || !nonce) return;
  let key = '';
  window.addEventListener('message', event => {
    const data = event.data;
    if (event.origin === origin && event.source === window.opener && data?.type === 'ap-study-credentials'
      && data.trial === trial && data.nonce === nonce) key = typeof data.key === 'string' ? data.key : '';
  });
  const send = detail => window.opener?.postMessage({type:'ap-study', trial, nonce, ...detail}, origin);
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, options) => {
    let targeted = false;
    try { targeted = new URL(typeof input === 'string' ? input : input.url, location.href).pathname === '/api/parse'; } catch (_) {}
    if (targeted && options?.body) {
      options = {...options, body:JSON.stringify({...JSON.parse(options.body), study_ai:mode,
        study_api_key:['gemma','nemotron','xing','lfm'].includes(mode)?key:undefined})};
    }
    const response = await originalFetch(input, options);
    if (targeted) response.clone().json().then(data => {
      if (data.study) send({event:'calculation', study:data.study, at:new Date().toISOString()});
      else send({event:'error', message:'연구 조건 확인 실패'});
    }).catch(() => send({event:'error', message:'계산 응답 확인 실패'}));
    return response;
  };
  const banner = document.createElement('div');
  banner.style.cssText='padding:16px 24px;background:#eaf2ff;border-bottom:2px solid #1769e0;color:#173c66;text-align:center;font:600 16px sans-serif';
  const label = {off:'AI 없음', qwen:'로컬 Qwen', gemma:'Gemma 4 31B · 무료', nemotron:'Nemotron 3 Super · 무료', xing:'Xing4.0 · 중국 · 무료', lfm:'LFM2.5 2.6B · 무료'}[mode];
  banner.textContent=`검증 연구 · ${label} · DDD / OLZ mg/day · 정답 제출은 연구 화면에서 해주세요.`;
  document.body.prepend(banner);
  const selector = document.querySelector('#base-method');
  if (selector) { selector.value='DDD'; selector.disabled=true; }
  const input = document.querySelector('#parser-input');
  if (input) input.value='';
  document.addEventListener('click', e => {
    if (e.target.closest('.learned-correction')) send({event:'suggestion_accepted', at:new Date().toISOString()});
    else if (e.target.closest('.manual-correction')) send({event:'manual_correction', at:new Date().toISOString()});
  });
  send({event:'ready', mode});
})();
