/* Preserve original-document browsing: categories first, then a source's modules. */
(function(){
'use strict';
const rows=()=>originalDocs().filter(a=>!a.demo&&!a.is_demo&&a.id!=='welcome-demo');
const topicRows=topic=>rows().filter(a=>(a.topic||'未分类')===topic);
const sourcesFor=topic=>[...new Set(topicRows(topic).map(a=>a.source||'我的资料'))];
function preferred(topic){const docs=topicRows(topic),sources=sourcesFor(topic);return (sources.includes('小林图解完整专栏')?'小林图解完整专栏':docs.find(a=>a.original_module)?.source)||sources[0]||'';}
let managing=false,deleting=false;const selected=new Set();
function addAction(){return managing?'<div class="material-actions"><span id="selection-count">已选 '+selected.size+' 篇</span><button class="secondary" id="cancel-manage">取消选择</button><button class="secondary danger" id="delete-materials" '+(!selected.size?'disabled':'')+'>删除所选</button></div>':'<div class="material-actions"><button class="ghost" id="manage-materials">管理资料</button><button class="secondary" id="release-add-materials">寻找或添加资料</button></div>';}
function updateSelection(){const count=$('#selection-count'),button=$('#delete-materials');if(count)count.textContent='已选 '+selected.size+' 篇';if(button)button.disabled=!selected.size||deleting;}
function bindAdd(){
 if(managing){
  $('#cancel-manage').onclick=()=>{managing=false;selected.clear();renderLibrary();};
  $('#delete-materials').onclick=confirmDelete;
  document.querySelectorAll('[data-book]').forEach(box=>box.onchange=()=>{
   const docs=rows().filter(a=>JSON.stringify([a.topic||'未分类',a.source||'我的资料'])===box.dataset.book);
   docs.forEach(a=>box.checked?selected.add(a.id):selected.delete(a.id));renderLibrary();
  });
 }else{
  $('#release-add-materials').onclick=()=>window.ReleaseUI.renderAddition();
  $('#manage-materials').onclick=()=>{managing=true;selected.clear();renderLibrary();};
 }
}
async function confirmDelete(){
 if(!selected.size||deleting)return;
 const ids=[...selected],docs=rows().filter(a=>selected.has(a.id));
 // Whole-source selection also removes hidden legacy fragments from that source.
 const keys=new Set(docs.map(a=>JSON.stringify([a.topic||'未分类',a.source||'我的资料'])));
 for(const key of keys){const book=rows().filter(a=>JSON.stringify([a.topic||'未分类',a.source||'我的资料'])===key);if(book.every(a=>selected.has(a.id)))for(const a of state.catalog)if(!a.is_demo&&JSON.stringify([a.topic||'未分类',a.source||'我的资料'])===key&&!ids.includes(a.id))ids.push(a.id);}
 const dialog=document.createElement('dialog');dialog.className='delete-material-dialog';dialog.setAttribute('aria-labelledby','delete-material-title');
 dialog.innerHTML='<h2 id="delete-material-title">删除所选资料？</h2><p>将删除 '+docs.length+' 篇资料及对应的本机资料文件，未完成待办也会移除，之后 AI 不会再安排这些资料。此操作无法撤销。</p><p class="muted">已有的学习记录、批注、对话和复习回答保留。</p><div class="material-actions"><button class="secondary" data-cancel>取消</button><button class="primary danger" data-confirm>确认删除</button></div><p role="status" data-error></p>';
 document.body.append(dialog);const close=()=>{dialog.close();dialog.remove();$('#delete-materials')?.focus();};
 dialog.querySelector('[data-cancel]').onclick=close;dialog.addEventListener('cancel',e=>{if(deleting)e.preventDefault();else{e.preventDefault();close();}});
 dialog.querySelector('[data-confirm]').onclick=async()=>{
  deleting=true;dialog.querySelectorAll('button').forEach(b=>b.disabled=true);dialog.querySelector('[data-confirm]').textContent='正在删除…';
  try{
   const result=await api('/api/resources/delete',{article_ids:ids}),removed=new Set(result.deleted_ids);
   state.catalog=state.catalog.filter(a=>!removed.has(a.id));selected.clear();managing=false;
   if(state.article&&removed.has(state.article.article.id)){hideReader();state.article=null;}
   close();await renderLibrary();toast(result.warnings?.length?'资料已从目录与计划移除；'+result.warnings.join('；'):'资料已删除，后续计划不会再安排');
  }catch(e){dialog.querySelector('[data-error]').textContent=e.message;dialog.querySelectorAll('button').forEach(b=>b.disabled=false);dialog.querySelector('[data-confirm]').textContent='重试删除';}
  finally{deleting=false;updateSelection();}
 };dialog.showModal();dialog.querySelector('[data-cancel]').focus();
}
function bookChoices(){
 const books=new Map();for(const a of rows()){const key=JSON.stringify([a.topic||'未分类',a.source||'我的资料']);if(!books.has(key))books.set(key,[]);books.get(key).push(a);}
 return '<p class="muted">可选择整份来源删除，或进入分类选择其中的篇目。</p><div class="original-contents">'+[...books].map(([key,docs])=>'<label class="contents-row material-book"><input type="checkbox" data-book="'+esc(key)+'" '+(docs.every(a=>selected.has(a.id))?'checked':'')+'><div><strong>'+esc(sourceLabel(docs[0].source||'我的资料'))+'</strong><div class="todo-meta">'+esc(docs[0].topic||'未分类')+' · '+docs.length+' 篇</div></div></label>').join('')+'</div>';
}
window.chooseSubject=function(topic){state.topic=topic;state.source=preferred(topic);state.query='';state.page=0;return renderLibrary();};
renderLibrary=async function(){
 const topics=[...new Set(rows().map(a=>a.topic||'未分类'))];
 if(state.topic&&!topics.includes(state.topic)){state.topic='';state.source='';}
 if(!state.topic){
  const groups=[['后端与基础',['Go后端','MySQL','Redis','计算机网络','操作系统','消息队列','Kafka','RabbitMQ','REST与接口设计','接口与系统设计','Linux与工程基础']],['前端',['JavaScript','TypeScript','Vue3','HTML','CSS']],['AI 与实习',['Agent','FastAPI','Harbor评测框架','Langfuse']]];
  const grouped=new Set(groups.flatMap(g=>g[1]));groups.push(['其他分类',topics.filter(t=>!grouped.has(t))]);
  $('#page').innerHTML=heading('资料库','先选一门，再沿原文目录学习。',addAction())+(managing?bookChoices():'')+`<div class="subject-index">${groups.filter(([,ts])=>ts.some(t=>topics.includes(t))).map(([name,ts])=>`<section class="subject-section"><h2>${esc(name)}</h2><div class="subject-grid">${ts.filter(t=>topics.includes(t)).map(t=>`<button class="subject-choice" data-subject="${esc(t)}"><strong>${esc(t)}</strong><small>${esc(sourceLabel(preferred(t)))}</small><span aria-hidden="true">›</span></button>`).join('')}</div></section>`).join('')}${topics.length?'':'<div class="empty"><h2>还没有资料</h2><p>添加想阅读的资料后，会在这里按分类显示。</p></div>'}</div>`;
  document.querySelectorAll('[data-subject]').forEach(b=>b.onclick=()=>chooseSubject(b.dataset.subject));bindAdd();return;
 }
 const sources=sourcesFor(state.topic);if(!sources.includes(state.source))state.source=preferred(state.topic);
 $('#page').innerHTML=`<nav class="library-crumb" aria-label="资料目录"><button class="ghost small" id="all-subjects">全部分类</button><span aria-hidden="true">/</span><strong>${esc(state.topic)}</strong></nav>`+heading(esc(state.topic),state.topic==='Go后端'?'沿用小林 coding 的 12 个原始模块，模块里的问题放在一起阅读。':'按原文篇目与章节阅读。',addAction())+`<div class="document-toolbar"><label>资料来源<select id="source-filter">${sources.map(s=>`<option value="${esc(s)}" ${state.source===s?'selected':''}>${esc(sourceLabel(s))}</option>`).join('')}</select></label><label class="document-search"><span class="sr-only">在当前目录搜索</span><input id="library-search" type="search" placeholder="在当前目录搜索" value="${esc(state.query)}"></label></div>${managing?`<label class="material-select-all"><input type="checkbox" id="select-source">选择当前来源的全部篇目</label>`:''}<div id="library-results"></div>`;
 $('#all-subjects').onclick=()=>{state.topic='';state.source='';state.query='';state.page=0;renderLibrary();};
 $('#source-filter').onchange=e=>{state.source=e.target.value;state.query='';state.page=0;renderLibrary();};
 $('#library-search').oninput=e=>{state.query=e.target.value;state.page=0;paintLibrary();};bindAdd();paintLibrary();
};
window.paintLibrary=function(){
 const query=(state.query||'').trim().toLowerCase();
 const all=topicRows(state.topic).filter(a=>(a.source||'我的资料')===state.source&&(!query||(a.title+' '+(a.group||'')).toLowerCase().includes(query))).sort((a,b)=>(a.order??999999)-(b.order??999999)||(a.path||'').localeCompare(b.path||''));
 const count=30,pages=Math.max(1,Math.ceil(all.length/count));state.page=Math.max(0,Math.min(state.page||0,pages-1));const page=all.slice(state.page*count,(state.page+1)*count),read=new Set(state.status?.read_ids||[]);
 $('#library-results').innerHTML=`<div class="filter-note"><span>${esc(sourceLabel(state.source))}</span><span>${all.length} 个原文${all.some(a=>a.original_module)?'模块':'篇目'}</span></div><div class="original-contents">${page.map((a,i)=>`<div class="contents-row">${managing?`<input type="checkbox" data-material="${esc(a.id)}" aria-label="选择 ${esc(a.title)}" ${selected.has(a.id)?'checked':''}>`:''}<span class="contents-order" aria-hidden="true">${state.page*count+i+1}</span><div><button class="article-button" data-read="${esc(a.id)}">${esc(a.title.replace('（完整文章）','').replace('（完整专栏）',''))}</button><div class="todo-meta">${a.original_module?'原文完整模块':'原文完整篇目'}${read.has(a.id)?' · 已读':''}</div></div><span class="todo-time">约 ${a.minutes||1} 分钟</span></div>`).join('')||'<div class="empty"><h2>没有匹配的篇目</h2><p>试试其他关键词，或切换资料来源。</p></div>'}</div>${pages>1?`<div class="pagination"><button class="secondary small" id="lib-prev" ${state.page===0?'disabled':''}>上一页</button><span>${state.page+1} / ${pages}</span><button class="secondary small" id="lib-next" ${state.page+1>=pages?'disabled':''}>下一页</button></div>`:''}`;
 if(managing){
  document.querySelectorAll('[data-material]').forEach(box=>box.onchange=()=>{box.checked?selected.add(box.dataset.material):selected.delete(box.dataset.material);updateSelection();paintLibrary();});
  const source=$('#select-source'),docs=topicRows(state.topic).filter(a=>(a.source||'我的资料')===state.source);
  source.checked=docs.length>0&&docs.every(a=>selected.has(a.id));source.indeterminate=!source.checked&&docs.some(a=>selected.has(a.id));source.onchange=()=>{docs.forEach(a=>source.checked?selected.add(a.id):selected.delete(a.id));updateSelection();paintLibrary();};
 }
 $('#lib-prev')?.addEventListener('click',()=>{state.page--;paintLibrary();});$('#lib-next')?.addEventListener('click',()=>{state.page++;paintLibrary();});
};
})();
