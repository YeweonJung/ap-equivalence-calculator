// Exercise the real click handler: displaying a candidate never submits it.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = {};
for (const id of ['parse-button','parser-input','parse-results','export-quick','download-status']) {
  elements['#'+id] = {value:'',textContent:'',innerHTML:'',disabled:false,hidden:true,
    dataset:{apiUrl:'/api/parse',exportUrl:'/api/export'},events:{},
    addEventListener(name,handler) {this.events[name]=handler;}};
}
const requests = [];
const context = vm.createContext({document:{querySelector:id=>elements[id]},
  location:{protocol:'https:'},AbortController,
  fetch:(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}))});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/quick_check.js'),'utf8'),context);
async function main() {
  const input = elements['#parser-input'];
  input.value = '로핀 1mg QD';
  const check = elements['#parse-button'].events.click();
  requests[0].resolve({ok:true,headers:{get:()=> 'application/json'},json:async()=>({
    items:[{ok:false,original:input.value,error:'약물 미확인',source_start:0,source_end:Array.from(input.value).length,
      suggestions:[{alias:'로도핀',drug:'zotepine',distance:1,explanation:'직접 확인하세요.',replacement:'로도핀 1mg QD'}]}],totals:[]})});
  await check;
  assert.equal(requests.length,1);
  assert.equal(input.value,'로핀 1mg QD');
  assert(elements['#parse-results'].innerHTML.includes('로도핀'));
  const selected={dataset:{item:'0',candidate:'0'}};
  elements['#parse-results'].events.click({target:{closest:()=>selected}});
  assert.equal(requests.length,2);
  assert.equal(JSON.parse(requests[1].options.body).text,'로도핀 1mg QD');
  console.log('Manual candidate selection submits only after an explicit click; dose and frequency preserved');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
