const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = {};
for (const id of ['parse-button','parser-input','parse-results','export-quick','download-status','base-method','supplement-order']) {
  elements['#'+id] = {value:'',textContent:'',innerHTML:'',disabled:false,hidden:true,
    dataset:{apiUrl:'/api/parse',exportUrl:'/api/export',priority:'CMD,MED,ED95,DDD,GARDNER,WOODS,CPZ_FGA,CMD_DIRECT,CMD_INDIRECT'}, events:{},
    addEventListener(event, handler) { this.events[event] = handler; }};
}
const requests=[];
const context=vm.createContext({document:{querySelector:id=>elements[id]},
  location:{protocol:'https:'},AbortController,
  fetch:(_,options)=>new Promise(resolve=>requests.push({resolve,options}))});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/quick_check.js'),'utf8'),context);
const response = data => ({ok:true,headers:{get:()=> 'application/json'},json:async()=>data});
const data = {items:[],totals:[]};
async function main() {
  assert.equal(elements['#supplement-order'].textContent,'MED → ED95 → DDD → GARDNER → WOODS → CPZ_FGA → CMD_DIRECT → CMD_INDIRECT');
  const input=elements['#parser-input'], button=elements['#parse-button'];
  input.value='old'; const old=button.events.click();
  input.value='new'; input.events.input();
  assert(requests[0].options.signal.aborted);
  const latest=button.events.click();
  requests[1].resolve(response(data)); await latest;
  const html=elements['#parse-results'].innerHTML;
  assert(html.includes('quick-totals'));
  assert(!html.includes('quick-scenarios'));
  requests[0].resolve(response({items:[{bad:true}],totals:[]})); await old;
  assert.equal(elements['#parse-results'].innerHTML,html);
  assert.equal(button.disabled,false);
  input.value='scenario'; const scenarioRun=button.events.click();
  requests[2].resolve(response({
    items:[],totals:[{method:'CMD',target_drug:'risperidone',total_equivalent_dose_mg:3}],
    cases:[{case_id:'CMD<script>alert(1)</script>',base:'CMD',complement:'<b>MED</b>',target:'RIS',
      total:null,partial:10.25,status:'미환산 <script>',methods:'CMD + MED <img>',missing:1,supplemented:2,
      note:'<svg onload=alert(1)>',details:[{original:'원문 <img>',drug:'약물 <script>',actual:'<u>MED</u>',target:'RIS',
        dose:5,factor:2,value:10.25,status:'ok',reason:'근거 <script>',basis:'basis <b>',source:'출처 <img src=x onerror=alert(1)>',
        case_id:'CMD+MED',base:'CMD',note:'detail note'}]}]
  })); await scenarioRun;
  const scenarioHtml=elements['#parse-results'].innerHTML;
  assert(scenarioHtml.indexOf('quick-scenarios') < scenarioHtml.indexOf('scenario-details'));
  assert(scenarioHtml.indexOf('scenario-details') < scenarioHtml.indexOf('original-totals'));
  assert(scenarioHtml.includes('합산 불가 · RIS · 부분합 10.25 mg/day'));
  assert(scenarioHtml.includes('CMD + MED &lt;img&gt;'));
  assert(scenarioHtml.includes('&lt;b&gt;MED&lt;/b&gt;'));
  assert(scenarioHtml.includes('미환산 1건'));
  assert(scenarioHtml.includes('보완 2건'));
  assert(scenarioHtml.includes('10.25 mg/day · RIS'));
  assert(scenarioHtml.includes('<td>&lt;u&gt;MED&lt;/u&gt;</td>'));
  assert(!scenarioHtml.slice(0, scenarioHtml.indexOf('scenario-details')).includes('원문 &lt;img&gt;'));
  assert(scenarioHtml.includes('근거 &lt;script&gt;'));
  assert(scenarioHtml.includes('출처 &lt;img src=x onerror=alert(1)&gt;'));
  assert(!scenarioHtml.includes('<script>'));
  assert(!scenarioHtml.includes('<img'));
  assert.equal(vm.runInContext('formatDose(100/30)',context),'3.3333');
  context.item={ok:false, original:'unknownxyz 2mg QD', error:'약물 미확인',
    status_label:'b: 인식불가', review_required:false};
  const unknownHtml=vm.runInContext('itemHtml(item,0)',context);
  assert(unknownHtml.includes('b: 인식불가') && !unknownHtml.includes('parse-item error'));
  context.item={ok:false, original:'risperidone -2mg QD', error:'용량은 0보다 커야 합니다.',
    status_label:'x: 오류 · 검토필요', review_required:true};
  assert(vm.runInContext('itemHtml(item,0)',context).includes('parse-item error'));
  context.item={ok:true,drug:'<script>',daily_dose_mg:2,route:'oral',status_message:'ok',
    conversions:[{method:'WOODS',target:'chlorpromazine',value:null}]};
  const rendered=vm.runInContext('itemHtml(item,0)',context);
  assert(rendered.includes('해당 방법의 계수 없음'));
  assert(rendered.includes('&lt;script&gt;'));
  context.item={ok:true,drug:'risperidone',route:'injection',needs_review:false,
    status_message:'환산 완료',warning:'',calculation_note:'경구 대응용량 기반 추정 <script>',conversions:[]};
  const injectionHtml=vm.runInContext('itemHtml(item,0)',context);
  assert(injectionHtml.includes('경구 대응용량 기반 추정 &lt;script&gt;'));
  assert(!injectionHtml.includes('검토 필요'));
  context.item={ok:false,original:'risperidnoe 2mg',error:'약물 미확인',
    suggestions:[{alias:'risperidone',drug:'risperidone',distance:1,explanation:'9번째 순서 교환: no → on <unsafe>'}]};
  const candidateHtml=vm.runInContext('itemHtml(item,0)',context);
  assert(!candidateHtml.includes('data-candidate'));
  assert(!candidateHtml.includes('unsafe'));
  assert(!candidateHtml.includes('AI'));
  const base=elements['#base-method'];
  base.value='DDD';
  const oldBase=button.events.click();
  assert.equal(JSON.parse(requests[3].options.body).base_method,'DDD');
  base.value='MED'; base.events.change();
  assert.equal(elements['#supplement-order'].textContent,'CMD → ED95 → DDD → GARDNER → WOODS → CPZ_FGA → CMD_DIRECT → CMD_INDIRECT');
  assert(requests[3].options.signal.aborted);
  requests[3].resolve(response(data)); await oldBase;
  assert.equal(elements['#parse-results'].textContent,'');
  assert.equal(elements['#export-quick'].hidden,true);
  const newBase=button.events.click();
  assert.equal(JSON.parse(requests[4].options.body).base_method,'MED');
  requests[4].resolve(response({items:[{ok:true,conversions:[]}],totals:[],cases:[]})); await newBase;
  const exporting=elements['#export-quick'].events.click();
  assert.equal(JSON.parse(requests[5].options.body).base_method,'MED');
  requests[5].resolve({ok:false,headers:{get:()=>''}}); await exporting;
  console.log('UI request ordering, selected base, export, summaries and escaping passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
context.totals = [{method:'CMD',target_drug:'olanzapine',total_equivalent_dose_mg:12.5,unresolved_count:0},
 {method:'WOODS',target_drug:'chlorpromazine',total_equivalent_dose_mg:null,partial_equivalent_dose_mg:100,unresolved_count:1}];
const summary = vm.runInContext('totalsHtml(totals, 3)',context);
assert(summary.includes('입력 약물 3개'));
assert(summary.includes('12.5'));
assert(summary.includes('합산 불가'));
assert(summary.includes('부분합 100 mg/day'));
assert(summary.includes('미환산 1건'));
