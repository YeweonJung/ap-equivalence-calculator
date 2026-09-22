const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const element = {addEventListener() {}};
const context = vm.createContext({document: {querySelector: () => element}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/quick_check.js'), 'utf8'), context);
context.item = {ok: false, original: 'zzzzzz 2mg', error: 'unknown', suggestions: [{
  alias: 'aripiprazole', drug: 'aripiprazole', source: 'llm', distance: null,
  explanation: '<script>untrusted reason</script>'
}]};
const html = vm.runInContext('itemHtml(item, 0)', context);
assert(html.includes('AI 미확인 후보'));
assert(!html.includes('글자 편집'));
assert(html.includes('&lt;script&gt;'));
assert(!html.includes('<script>'));
assert(html.includes('data-candidate="0"'));
console.log('LLM labels, selection wiring and reason escaping passed');
