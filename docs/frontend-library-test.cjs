const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();const element=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'',addEventListener(type,fn){this['on'+type]=fn}});return nodes.get(s)};
const context={state:{topic:'',source:'',query:'',page:0,catalog:[
 {id:'extra',title:'补充问题',topic:'Go后端',source:'补充笔记',path:'资料源/extra.md',learning_unit:true,order:0},
 {id:'map',title:'Map',topic:'Go后端',source:'原始主专栏',path:'a.html',learning_unit:true,original_module:true,order:2},
 {id:'base',title:'基础',topic:'Go后端',source:'原始主专栏',path:'b.html',learning_unit:true,original_module:true,order:0},
 {id:'vue',title:'Vue',topic:'Vue3',source:'Vue文档',path:'资料源/vue.md',learning_unit:true},
 {id:'agent',title:'Agent',topic:'Agent',source:'Agent文档',path:'资料源/agent.md',learning_unit:true},
 {id:'photo',title:'摄影构图',topic:'摄影',source:'构图文档',path:'资料源/photo.md',learning_unit:true}
 ],status:{read_ids:['base']}},$ : element,esc:v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x])),heading:(t,d,a)=>'<h1>'+t+'</h1>'+a,go:()=>Promise.resolve(),document:{querySelectorAll(selector){if(selector==='[data-subject]')return [...element('#page').innerHTML.matchAll(/data-subject="([^"]+)"/g)].map(m=>({dataset:{subject:m[1]}}));return []},querySelector:()=>null}};
context.window=context;vm.createContext(context);vm.runInContext(fs.readFileSync('static/library.js','utf8'),context);vm.runInContext(fs.readFileSync('static/release-library.js','utf8'),context);
(async()=>{
 await vm.runInContext('renderLibrary()',context);let html=element('#page').innerHTML;
 assert(html.includes('<h2>后端与基础</h2>')&&html.includes('<h2>前端</h2>')&&html.includes('<h2>AI 与实习</h2>'),'original category group headings must remain');assert(html.indexOf('后端与基础')<html.indexOf('data-subject="Go后端"'));assert(html.indexOf('<h2>前端</h2>')<html.indexOf('data-subject="Vue3"'));assert(html.includes('<h2>其他分类</h2>'),'custom categories remain visible');
 assert(html.includes('data-subject="Go后端"'),'library home must be category choices');assert(html.includes('data-subject="摄影"'),'new imported categories are dynamic');assert(!html.includes('data-read='),'home must not flatten all articles');
 await vm.runInContext('chooseSubject("Go后端")',context);assert.equal(context.state.source,'原始主专栏','prefer complete original modules');html=element('#library-results').innerHTML;
 assert(html.includes('data-read="base"'));assert(html.indexOf('data-read="base"')<html.indexOf('data-read="map"'));assert(!html.includes('data-read="extra"'));assert(html.includes('已读'));
 element('#source-filter').onchange({target:{value:'补充笔记'}});html=element('#library-results').innerHTML;assert(html.includes('data-read="extra"'));assert(!html.includes('data-read="base"'));
 element('#all-subjects').onclick();assert.equal(context.state.topic,'');assert(element('#page').innerHTML.includes('data-subject="摄影"'));assert(element('#page').innerHTML.includes('id="manage-materials"'),'library offers selection management');
 element('#manage-materials').onclick();assert(element('#page').innerHTML.includes('data-book='),'manage mode offers whole source selection');
 await vm.runInContext('chooseSubject("Go后端")',context);assert(element('#library-results').innerHTML.includes('data-material="base"'),'manage mode offers per-module selection');
 element('#cancel-manage').onclick();assert(!element('#library-results').innerHTML.includes('data-material='),'cancel returns to reading');
 console.log('hierarchical library and deletion selection passed');
})().catch(e=>{console.error(e);process.exit(1)});
