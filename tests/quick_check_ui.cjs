const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = {};
for (const id of ['parse-button','parser-input','parse-results','export-quick','download-status']) {
  elements['#'+id] = {value:'',textContent:'',innerHTML:'',disabled:false,hidden:true,
    dataset:{apiUrl:'/api/parse',exportUrl:'/api/export'}, events:{},
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
  const input=elements['#parser-input'], button=elements['#parse-button'];
  input.value='old'; const old=button.events.click();
  input.value='new'; input.events.input();
  assert(requests[0].options.signal.aborted);
  const latest=button.events.click();
  requests[1].resolve(response(data)); await latest;
  const html=elements['#parse-results'].innerHTML;
  requests[0].resolve(response({items:[{bad:true}],totals:[]})); await old;
  assert.equal(elements['#parse-results'].innerHTML,html);
  assert.equal(button.disabled,false);
  assert.equal(vm.runInContext('formatDose(100/30)',context),'3.3333');
  context.item={ok:true,drug:'<script>',daily_dose_mg:2,route:'oral',status_message:'ok',
    conversions:[{method:'WOODS',target:'chlorpromazine',value:null}]};
  const rendered=vm.runInContext('itemHtml(item,0)',context);
  assert(rendered.includes('해당 방법의 계수 없음'));
  assert(rendered.includes('&lt;script&gt;'));
  context.item={ok:false,original:'risperidnoe 2mg',error:'약물 미확인',
    suggestions:[{alias:'risperidone',drug:'risperidone',distance:1,explanation:'9번째 순서 교환: no → on <unsafe>'}]};
  const candidateHtml=vm.runInContext('itemHtml(item,0)',context);
  assert(candidateHtml.includes('순서 교환'));
  assert(candidateHtml.includes('&lt;unsafe&gt;'));
  assert(candidateHtml.includes('data-candidate="0"'));
  console.log('UI request ordering, rounding, missing factors and escaping passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
