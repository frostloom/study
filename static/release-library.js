/* Preserve original-document browsing: categories first, then a source's modules. */
(function(){
'use strict';
const rows=()=>originalDocs().filter(a=>!a.demo&&!a.is_demo&&a.id!=='welcome-demo');
const topicRows=topic=>rows().filter(a=>(a.topic||'未分类')===topic);
const sourcesFor=topic=>[...new Set(topicRows(topic).map(a=>a.source||'我的资料'))];
function preferred(topic){const docs=topicRows(topic),sources=sourcesFor(topic);return (sources.includes('小林图解完整专栏')?'小林图解完整专栏':docs.find(a=>a.original_module)?.source)||sources[0]||'';}
function addAction(){return '<button class="secondary" id="release-add-materials">寻找或添加资料</button>';}
function bindAdd(){$('#release-add-materials').onclick=()=>go('settings').then(()=>document.querySelector('[data-settings-tab="materials"]')?.click());}
window.chooseSubject=function(topic){state.topic=topic;state.source=preferred(topic);state.query='';state.page=0;return renderLibrary();};
renderLibrary=async function(){
 const topics=[...new Set(rows().map(a=>a.topic||'未分类'))];
 if(state.topic&&!topics.includes(state.topic)){state.topic='';state.source='';}
 if(!state.topic){
  const groups=[['后端与基础',['Go后端','MySQL','Redis','计算机网络','操作系统','消息队列','Kafka','RabbitMQ','REST与接口设计','接口与系统设计','Linux与工程基础']],['前端',['JavaScript','TypeScript','Vue3','HTML','CSS']],['AI 与实习',['Agent','FastAPI','Harbor评测框架','Langfuse']]];
  const grouped=new Set(groups.flatMap(g=>g[1]));groups.push(['其他分类',topics.filter(t=>!grouped.has(t))]);
  $('#page').innerHTML=heading('资料库','',addAction())+`<div class="subject-index">${groups.filter(([,ts])=>ts.some(t=>topics.includes(t))).map(([name,ts])=>`<section class="subject-section"><h2>${esc(name)}</h2><div class="subject-grid">${ts.filter(t=>topics.includes(t)).map(t=>`<button class="subject-choice" data-subject="${esc(t)}"><strong>${esc(t)}</strong><small>${esc(sourceLabel(preferred(t)))}</small><span aria-hidden="true">›</span></button>`).join('')}</div></section>`).join('')}${topics.length?'':'<div class="empty"><h2>还没有资料</h2><p>添加想阅读的资料后，会在这里按分类显示。</p></div>'}</div>`;
  document.querySelectorAll('[data-subject]').forEach(b=>b.onclick=()=>chooseSubject(b.dataset.subject));bindAdd();return;
 }
 const sources=sourcesFor(state.topic);if(!sources.includes(state.source))state.source=preferred(state.topic);
 $('#page').innerHTML=`<nav class="library-crumb" aria-label="资料目录"><button class="ghost small" id="all-subjects">全部分类</button><span aria-hidden="true">/</span><strong>${esc(state.topic)}</strong></nav>`+heading(esc(state.topic),'',addAction())+`<div class="document-toolbar"><label>资料来源<select id="source-filter">${sources.map(s=>`<option value="${esc(s)}" ${state.source===s?'selected':''}>${esc(sourceLabel(s))}</option>`).join('')}</select></label><label class="document-search"><span class="sr-only">在当前目录搜索</span><input id="library-search" type="search" placeholder="在当前目录搜索" value="${esc(state.query)}"></label></div><div id="library-results"></div>`;
 $('#all-subjects').onclick=()=>{state.topic='';state.source='';state.query='';state.page=0;renderLibrary();};
 $('#source-filter').onchange=e=>{state.source=e.target.value;state.query='';state.page=0;renderLibrary();};
 $('#library-search').oninput=e=>{state.query=e.target.value;state.page=0;paintLibrary();};bindAdd();paintLibrary();
};
window.paintLibrary=function(){
 const query=(state.query||'').trim().toLowerCase();
 const all=topicRows(state.topic).filter(a=>(a.source||'我的资料')===state.source&&(!query||(a.title+' '+(a.group||'')).toLowerCase().includes(query))).sort((a,b)=>(a.order??999999)-(b.order??999999)||(a.path||'').localeCompare(b.path||''));
 const count=30,pages=Math.max(1,Math.ceil(all.length/count));state.page=Math.max(0,Math.min(state.page||0,pages-1));const page=all.slice(state.page*count,(state.page+1)*count),read=new Set(state.status?.read_ids||[]);
 $('#library-results').innerHTML=`<div class="filter-note"><span>${esc(sourceLabel(state.source))}</span><span>${all.length} 个原文${all.some(a=>a.original_module)?'模块':'篇目'}</span></div><div class="original-contents">${page.map((a,i)=>`<div class="contents-row"><span class="contents-order" aria-hidden="true">${state.page*count+i+1}</span><div><button class="article-button" data-read="${esc(a.id)}">${esc(a.title.replace('（完整文章）','').replace('（完整专栏）',''))}</button><div class="todo-meta">${a.original_module?'原文完整模块':'原文完整篇目'}${read.has(a.id)?' · 已读':''}</div></div><span class="todo-time">约 ${a.minutes||1} 分钟</span></div>`).join('')||'<div class="empty"><h2>没有匹配的篇目</h2><p>试试其他关键词，或切换资料来源。</p></div>'}</div>${pages>1?`<div class="pagination"><button class="secondary small" id="lib-prev" ${state.page===0?'disabled':''}>上一页</button><span>${state.page+1} / ${pages}</span><button class="secondary small" id="lib-next" ${state.page+1>=pages?'disabled':''}>下一页</button></div>`:''}`;
 $('#lib-prev')?.addEventListener('click',()=>{state.page--;paintLibrary();});$('#lib-next')?.addEventListener('click',()=>{state.page++;paintLibrary();});
};
})();
