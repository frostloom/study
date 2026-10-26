const fs=require('fs'),vm=require('vm'),assert=require('assert');const ctx={window:{},setTimeout,clearTimeout};vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/ai-compose.js','utf8'),ctx);
let sent=0,saved=0;const input={value:'my question',addEventListener(k,fn){this[k]=fn},focus(){}};ctx.window.AICompose.bindInput(input,{send:()=>sent++,clear:()=>{input.value='';saved++}});
function key(extra){let prevented=false;input.keydown({key:'Enter',preventDefault(){prevented=true},...extra});return prevented}
assert(key({}));assert.equal(sent,1);assert(!key({shiftKey:true}));assert.equal(sent,1);assert(!key({isComposing:true}));assert(!key({keyCode:229}));assert.equal(sent,1);assert(key({ctrlKey:true}));assert.equal(sent,2);
assert(key({key:'Backspace',ctrlKey:true,shiftKey:true}));assert.equal(input.value,'');assert.equal(saved,1);input.value='next';assert(!key({key:'Backspace',ctrlKey:true}));assert.equal(input.value,'next');
const drawer=fs.readFileSync('static/ai-drawer.js','utf8'),clearFn=drawer.match(/function aiClearQuestion\(\)\{[^\n]+\}/)[0];const box={value:'Question',focus(){}};const clearCtx={aiQuote:'Quoted source',$:()=>box,aiSaveDraft(){this.saved=true}};vm.createContext(clearCtx);vm.runInContext(clearFn+';aiClearQuestion()',clearCtx);assert.equal(box.value,'');assert.equal(clearCtx.aiQuote,'Quoted source');
input.compositionstart();assert(!key({isComposing:false,keyCode:13}));assert.equal(sent,2);input.compositionend();
console.log('Enter/Shift+Enter, IME and clear-question-only shortcuts passed');
