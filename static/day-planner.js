/* Edit a day's workload without changing the global learning preferences. */
(function(){
'use strict';
let active=null;
const documents=()=>originalDocs().filter(a=>!a.is_demo&&!a.demo);
const tasks=p=>(p?.items||[]).filter(x=>!x.deleted).map(x=>({article_id:x.article_id,minutes:x.minutes,scope:x.scope||''}));
function openDialog(title){
 if(active)return null;
 const el=document.createElement('dialog');el.className='day-planner-dialog';el.setAttribute('aria-labelledby','day-planner-title');
 el.innerHTML=`<header><div><h2 id="day-planner-title">${title}</h2><p>只调整 ${esc(state.day)}，不修改默认学习时长。</p></div><button class="ghost" data-close aria-label="关闭任务设置">关闭</button></header><div class="day-planner-body"></div><footer><p role="status" data-error></p><div class="material-actions"><button class="secondary" data-cancel>取消</button><button class="primary" data-save>保存</button></div></footer>`;
 document.body.append(el);active=el;let pending=false,disabledStates=new Map();const opener=document.activeElement;
 const close=()=>{if(pending)return;el.close();el.remove();active=null;opener?.focus();};
 el.querySelector('[data-close]').onclick=close;el.querySelector('[data-cancel]').onclick=close;
 el.addEventListener('cancel',e=>{e.preventDefault();close();});el.showModal();
 return {el,body:el.querySelector('.day-planner-body'),close,setBusy(v){pending=v;if(v){disabledStates=new Map([...el.querySelectorAll('button,input,select')].map(x=>[x,x.disabled]));disabledStates.forEach((_,x)=>x.disabled=true);}else disabledStates.forEach((disabled,x)=>x.disabled=disabled);el.querySelector('[data-save]').textContent=v?'正在保存…':'保存';}};
}
async function persist(dialog,day,plan,newTasks,budget){
 dialog.setBusy(true);dialog.el.querySelector('[data-error]').textContent='';
 try{
  await api('/api/plan/edit',{date:day,action:'save',tasks:newTasks,expected_revision:plan?.revision||'',...budget});
  dialog.setBusy(false);dialog.close();if(state.view==='today'&&state.day===day)await renderToday();toast('当天计划已更新，晚间复习会跟随实际完成内容');
 }catch(e){dialog.setBusy(false);dialog.el.querySelector('[data-error]').textContent=e.message;}
}
function showAdd(){
 const dialog=openDialog('添加学习章节');if(!dialog)return;
 const day=state.day,plan=state.plan,chosen=new Map(),already=new Set(tasks(plan).map(x=>x.article_id)),docs=documents();
 const topics=[...new Set(docs.map(a=>a.topic||'未分类'))];let topic=topics[0]||'',source='',query='';
 dialog.body.innerHTML=`<div class="day-picker-filters"><label>分类<select data-topic>${topics.map(t=>`<option>${esc(t)}</option>`).join('')}</select></label><label>资料来源<select data-source></select></label><label>搜索章节<input type="search" data-search placeholder="章节名称"></label></div><div data-choices class="day-chapter-choices"></div><section class="day-picked"><h3 data-count>待加入 0 个章节</h3><div data-picked></div></section>`;
 const sourceSelect=dialog.el.querySelector('[data-source]');
 function sources(){const options=[...new Set(docs.filter(a=>(a.topic||'未分类')===topic).map(a=>a.source||'我的资料'))];source=options[0]||'';sourceSelect.innerHTML=options.map(s=>`<option value="${esc(s)}">${esc(sourceLabel(s))}</option>`).join('');}
 function picked(){
  dialog.el.querySelector('[data-count]').textContent='待加入 '+chosen.size+' 个章节';dialog.el.querySelector('[data-save]').disabled=!chosen.size;
  dialog.el.querySelector('[data-picked]').innerHTML=[...chosen.values()].map(t=>{const a=docs.find(x=>x.id===t.article_id);return `<div class="day-task-editor"><strong>${esc(a.title)}</strong><label>本次阅读（分钟）<input data-minutes="${esc(a.id)}" type="number" min="1" max="${a.minutes}" value="${t.minutes}"></label><label class="day-task-scope">本次范围<input data-scope="${esc(a.id)}" maxlength="1000" placeholder="例如：第 1–3 小节；留空则按原文阅读" value="${esc(t.scope)}"></label><button class="ghost small" data-unpick="${esc(a.id)}">移除</button></div>`;}).join('');
  dialog.el.querySelectorAll('[data-minutes]').forEach(i=>i.oninput=()=>chosen.get(i.dataset.minutes).minutes=Number(i.value));
  dialog.el.querySelectorAll('[data-scope]').forEach(i=>i.oninput=()=>chosen.get(i.dataset.scope).scope=i.value);
  dialog.el.querySelectorAll('[data-unpick]').forEach(b=>b.onclick=()=>{chosen.delete(b.dataset.unpick);paint();picked();});
 }
 function paint(){
  const matches=docs.filter(a=>(a.topic||'未分类')===topic&&(a.source||'我的资料')===source&&a.title.toLowerCase().includes(query.toLowerCase())).sort((a,b)=>(a.order??99999)-(b.order??99999));
  dialog.el.querySelector('[data-choices]').innerHTML=matches.map(a=>`<label class="day-chapter-choice"><input type="checkbox" data-pick="${esc(a.id)}" ${already.has(a.id)?'disabled checked':chosen.has(a.id)?'checked':''}><span>${esc(a.title)}<small>${already.has(a.id)?'已在当天清单':`原文约 ${a.minutes} 分钟`}</small></span></label>`).join('')||'<p class="muted">没有匹配的章节，请切换来源或关键词。</p>';
  dialog.el.querySelectorAll('[data-pick]').forEach(i=>i.onchange=()=>{const a=docs.find(x=>x.id===i.dataset.pick);if(i.checked)chosen.set(a.id,{article_id:a.id,minutes:plan?.removed_items?.find(x=>x.article_id===a.id&&x.done)?.minutes??a.minutes,scope:plan?.removed_items?.find(x=>x.article_id===a.id&&x.done)?.scope||''});else chosen.delete(a.id);picked();});
 }
 dialog.el.querySelector('[data-topic]').onchange=e=>{topic=e.target.value;sources();paint();};sourceSelect.onchange=e=>{source=e.target.value;paint();};dialog.el.querySelector('[data-search]').oninput=e=>{query=e.target.value;paint();};
 dialog.el.querySelector('[data-save]').onclick=()=>persist(dialog,day,plan,tasks(plan).concat([...chosen.values()]));
 sources();paint();picked();dialog.el.querySelector('[data-topic]').focus();
}
function showEdit(){
 const dialog=openDialog('调整当天计划');if(!dialog)return;
 const day=state.day,plan=state.plan,items=tasks(plan);let drafts=items.map(x=>({...x}));
 const prefs=state.profile||{daily_minutes:90,review_minutes:30};
 dialog.body.innerHTML=`<div class="day-budget-fields"><label>当天阅读预算（分钟）<input type="number" data-reading min="0" max="475" value="${plan?.reading_minutes??prefs.daily_minutes-prefs.review_minutes}"></label><label>当天复习（分钟）<input type="number" data-review min="5" max="480" value="${plan?.review_minutes??prefs.review_minutes}"></label></div><p class="muted">移除章节只调整当天待办，不删除书籍。已提交的复习回答和真实完成记录会保留；已完成任务需先取消勾选，才能修改阅读范围。</p><div data-edit-tasks></div><p data-estimate class="muted"></p>`;
 function paint(){
  dialog.el.querySelector('[data-edit-tasks]').innerHTML=drafts.map(t=>{const a=state.catalog.find(x=>x.id===t.article_id),done=plan?.items.find(x=>x.article_id===t.article_id)?.done;return `<div class="day-task-editor"><strong>${esc(a?.title||t.article_id)}${done?' · 已完成':''}</strong><label>本次阅读（分钟）<input data-minutes="${esc(t.article_id)}" type="number" min="1" max="${a?.minutes||120}" value="${t.minutes}" ${done?'disabled':''}></label><label class="day-task-scope">本次范围<input data-scope="${esc(t.article_id)}" maxlength="1000" value="${esc(t.scope)}" ${done?'disabled':''}></label><button class="ghost small" data-remove-task="${esc(t.article_id)}">移除</button></div>`;}).join('')||'<p class="muted">当天没有阅读任务。可以返回添加章节。</p>';
  const total=()=>dialog.el.querySelector('[data-estimate]').textContent='当前清单共 '+drafts.reduce((n,x)=>n+x.minutes,0)+' 分钟';
  dialog.el.querySelectorAll('[data-minutes]').forEach(i=>i.oninput=()=>{drafts.find(t=>t.article_id===i.dataset.minutes).minutes=Number(i.value);total();});
  dialog.el.querySelectorAll('[data-scope]').forEach(i=>i.oninput=()=>drafts.find(t=>t.article_id===i.dataset.scope).scope=i.value);
  dialog.el.querySelectorAll('[data-remove-task]').forEach(b=>b.onclick=()=>{drafts=drafts.filter(t=>t.article_id!==b.dataset.removeTask);paint();});total();
 }
 dialog.el.querySelector('[data-save]').onclick=()=>persist(dialog,day,plan,drafts,{reading_minutes:Number(dialog.el.querySelector('[data-reading]').value),review_minutes:Number(dialog.el.querySelector('[data-review]').value)});
 paint();dialog.el.querySelector('[data-reading]').focus();
}
const original=renderToday;
renderToday=async function(){const day=state.day;await original();if(state.view!=='today'||day!==state.day)return;const heading=document.querySelector('#page .page-heading');if(!heading)return;document.querySelector('#day-plan-actions')?.remove();const buttons=document.createElement('div');buttons.id='day-plan-actions';buttons.className='material-actions';buttons.innerHTML='<button class="secondary" data-add-chapters>添加章节</button><button class="ghost" data-edit-day>调整计划</button>';heading.append(buttons);buttons.querySelector('[data-add-chapters]').onclick=showAdd;buttons.querySelector('[data-edit-day]').onclick=showEdit;if(state.plan)document.querySelector('#generate-plan').hidden=true;};
window.DayPlanner={showAdd,showEdit};
})();
