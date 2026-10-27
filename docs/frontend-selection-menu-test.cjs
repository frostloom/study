const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/app.js','utf8').replace(/\r\n/g,'\n');
const capture=source.slice(source.indexOf('function captureSelection('),source.indexOf('\nfunction applyHighlights('));
const marker=source.indexOf('let selectionCaptureTimer');
const start=marker<0?source.indexOf("$('#article-body').addEventListener('mouseup'"):marker;
const setup=source.slice(start,source.indexOf("\n$('#selection-menu').addEventListener",start));
const handlers=new Map(),nodes=new Map(),timers=new Map();let tid=0;
function node(id){if(!nodes.has(id))nodes.set(id,{hidden:false,open:false,style:{},addEventListener:(type,fn)=>handlers.set(id+':'+type,fn)});return nodes.get(id)}
node('#selection-menu').hidden=true;node('#article-body').contains=n=>n==='inside';
let valid=true,collapsed=false;
const range={commonAncestorContainer:'inside',startContainer:'inside',startOffset:0,toString:()=> '选中的原文',cloneRange:()=>({selectNodeContents(){},setEnd(){},toString:()=>''}),getBoundingClientRect:()=>({left:30,bottom:180})};
const ctx={$:node,state:{selection:null},window:{getSelection:()=>({isCollapsed:collapsed,rangeCount:1,getRangeAt:()=>range})},document:{addEventListener:(type,fn)=>handlers.set('document:'+type,fn)},setTimeout:fn=>{timers.set(++tid,fn);return tid},clearTimeout:id=>timers.delete(id),innerWidth:1000,innerHeight:700,aiSectionForNode:()=>2};
vm.createContext(ctx);vm.runInContext(capture+'\n'+setup,ctx);
function event(type){handlers.get('document:'+type)?.({target:node('#reader-scroll')});for(const [id,fn] of [...timers]){timers.delete(id);fn();}}
event('selectionchange');assert.equal(node('#selection-menu').hidden,false,'selection changes must show the menu without a mouseup inside the article');assert.equal(ctx.state.selection.quote,'选中的原文');assert.equal(ctx.state.selection.section_index,2);
node('#selection-menu').hidden=true;event('pointerup');assert.equal(node('#selection-menu').hidden,false,'release on reader margin should capture an existing article selection');
collapsed=true;event('selectionchange');assert.equal(node('#selection-menu').hidden,true,'clear menu when selection collapses');
collapsed=false;range.commonAncestorContainer='outside';event('selectionchange');assert.equal(node('#selection-menu').hidden,true,'never offer article actions for AI chat or another input');
range.commonAncestorContainer='inside';event('selectionchange');const saved=ctx.state.selection;node('#note-dialog').open=true;collapsed=true;event('selectionchange');assert.equal(ctx.state.selection,saved,'note editor focus must preserve its original quote until saved');
console.log('selectionchange, release outside article, clearing and annotation quote preservation passed');
