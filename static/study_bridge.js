/* Research popup bridge. Credentials stay in page memory and go only to our same-origin parse API. */
(() => {
  const params=new URLSearchParams(location.search),mode=params.get('study_ai');
  if(!mode)return;
  const origin=params.get('study_origin'),trial=params.get('study_trial'),nonce=params.get('study_nonce');
  const cloud=['google_flash','groq_oss120','groq_oss20','groq_qwen'];
  const origins=new Set(['https://ap-dose-validation.yewonjeong000.chatgpt.site','http://localhost:8088','http://127.0.0.1:8088']);
  const valid=['off','qwen',...cloud].includes(mode)&&origins.has(origin)&&trial&&nonce;
  let key='',confirmed=false,preview=params.get('study_preview')==='1',paused=false;
  const send=detail=>{if(valid)window.opener?.postMessage({type:'ap-study',trial,nonce,...detail},origin);};
  window.addEventListener('message',event=>{
    const data=event.data;
    if(valid&&event.origin===origin&&event.source===window.opener&&data?.type==='ap-study-credentials'&&data.trial===trial&&data.nonce===nonce){
      key=typeof data.key==='string'?data.key:'';
      confirmed=data.freeTierConfirmed===true;
      preview=preview||data.preview===true;
    }
  });
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(input,options)=>{
    let targeted=false;
    try{
      const url=new URL(typeof input==='string'?input:input.url,location.href);
      targeted=url.origin===location.origin&&url.pathname==='/api/parse';
    }catch(_){}
    if(targeted&&options?.body){
      options={...options,body:JSON.stringify({...JSON.parse(options.body),
        study_ai:valid?mode:'invalid_study_context',
        study_api_key:valid&&cloud.includes(mode)&&!preview&&!paused?key:undefined,
        study_free_tier_confirmed:valid&&confirmed&&!preview&&!paused,
        study_preview:preview})};
    }
    const response=await originalFetch(input,options);
    if(targeted)response.clone().json().then(data=>{
      if(data.study){
        if(data.study.calls?.some(c=>[402,429].includes(c.http_status))){paused=true;key='';confirmed=false;}
        send({event:'calculation',study:data.study,at:new Date().toISOString()});
      }else send({event:'error',message:'연구 조건 확인 실패'});
    }).catch(()=>send({event:'error',message:'계산 응답 확인 실패'}));
    return response;
  };
  const banner=document.createElement('div');
  banner.style.cssText='padding:16px 24px;background:#eaf2ff;border-bottom:2px solid #1769e0;color:#173c66;text-align:center;font:600 16px sans-serif';
  const label={off:'AI 없음',qwen:'로컬 Qwen',google_flash:'Gemini 3.8 Flash',groq_oss120:'GPT-OSS 120B',groq_oss20:'GPT-OSS 20B',groq_qwen:'Qwen3.8 27B · 중국'}[mode];
  banner.textContent=valid?'검증 연구 · '+label+(preview?' · 화면 점검: AI 요청 없음':'')+' · DDD / OLZ mg/day · 정답은 연구 화면에서 제출하세요.':'연구 연결이 올바르지 않습니다. 연구 화면에서 배정된 앱을 다시 여세요.';
  document.body.prepend(banner);
  const selector=document.querySelector('#base-method');
  if(selector){selector.value='DDD';selector.disabled=true;}
  const input=document.querySelector('#parser-input');if(input)input.value='';
  document.addEventListener('click',e=>{
    if(e.target.closest('.learned-correction'))send({event:'suggestion_accepted',at:new Date().toISOString()});
    else if(e.target.closest('.manual-correction'))send({event:'manual_correction',at:new Date().toISOString()});
  });
  send({event:'ready',mode});
})();
