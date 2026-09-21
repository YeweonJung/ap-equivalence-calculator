const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = {};
for (const id of ['parse-button','parser-input','parse-results','export-quick','download-status','feedback-status','feedback-consent-0','correct-name-0']) {
  elements['#'+id] = {value:'',textContent:'',innerHTML:'',checked:false,
    dataset:{apiUrl:'/api/parse'}, events:{}, addEventListener(n,h){this.events[n]=h;}};
}
const calls=[];
const context=vm.createContext({document:{querySelector:id=>elements[id]},location:{protocol:'https:'},AbortController,
  fetch:(url,options)=>{calls.push({url, body:JSON.parse(options.body)}); return Promise.resolve({ok:true,json:async()=>({message:'saved'})});}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/quick_check.js'),'utf8'),context);
context.item={feedback_token:'signed-token',correction_suffix:' 2mg BID'};
(async()=>{
  await vm.runInContext("recordCorrection(item,0,'할돌','candidate')",context);
  assert.equal(calls.length,0);
  elements['#feedback-consent-0'].checked=true;
  await vm.runInContext("recordCorrection(item,0,'할돌','candidate')",context);
  assert.deepEqual(calls[0],{url:'/api/name-feedback',body:{token:'signed-token',selected_alias:'할돌',source:'candidate',consent:true}});
  assert.equal(elements['#feedback-status'].textContent,'saved');
  vm.runInContext("currentText='할리l 2mg BID'; currentItems=[{...item,source_start:0,source_end:11}]; runQuickCheck=()=>{}",context);
  elements['#parser-input'].value='할리l 2mg BID';
  elements['#correct-name-0'].value='할돌';
  elements['#parse-results'].events.click({target:{closest:selector=>selector==='.manual-correction'?{dataset:{item:'0'}}:null}});
  assert.equal(elements['#parser-input'].value,'할돌 2mg BID');
  assert.equal(calls[1].body.source,'manual');
  console.log('Opt-in feedback and manual name correction preserve the dose and frequency');
})().catch(e=>{console.error(e);process.exitCode=1;});
