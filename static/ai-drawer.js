// AI is opened on demand. Drafts and requests belong to the article, not the panel.
const aiPending=new Map();
let aiQuote='',aiReturnFocus=null,aiSectionIndex=null;
const aiDraftKey=(id,sid=state.article?.session_id)=>'study-ai-draft:'+id+':'+(sid||'legacy');
const aiSessionKey=(id,sid)=>id+':'+sid;
let aiSessionSwitch=0;
function aiSaveDraft(){if(state.article)localStorage.setItem(aiDraftKey(state.article.article.id),JSON.stringify({question:$('#ask-input').value,quote:aiQuote,section_index:aiSectionIndex}));}
function aiSectionForNode(node){const hs=[...$('#article-body').querySelectorAll('h1,h2,h3,h4,h5,h6')];let index=0;for(let i=0;i<hs.length;i++){if(hs[i].contains(node)||(hs[i].compareDocumentPosition(node)&Node.DOCUMENT_POSITION_FOLLOWING))index=i;else break;}return hs.length?index:null;}
function aiVisibleSection(){const hs=[...$('#article-body').querySelectorAll('h1,h2,h3,h4,h5,h6')],top=$('#reader-scroll').getBoundingClientRect().top;let i=0;hs.forEach((h,n)=>{if(h.getBoundingClientRect().top<=top+100)i=n;});if(i===0&&hs.length>1&&(hs[0].tagName==='H1'||state.article?.article.original_module))i=1;return hs.length?i:null;}
function aiPaintSection(){const hs=$('#article-body').querySelectorAll('h1,h2,h3,h4,h5,h6'),h=hs[aiSectionIndex];$('#ai-section-label').textContent=h?'当前小节 · '+h.textContent.replace(/^#\s*/,''):'当前小节';}
function aiPaintQuote(){aiPaintSection();const box=$('#selected-quote');box.hidden=!aiQuote;$('#quote-text').textContent=aiQuote;}
function aiSyncViewport(){if(state.article)$('#reader-scroll').inert=$('#reader').classList.contains('ai-open')&&matchMedia('(max-width:760px)').matches;}
function resetAIForArticle(keepOpen=false){
 if(!keepOpen){$('#reader').classList.remove('ai-open','ai-collapsed');$('#ai-drawer').hidden=true;$('#reader-scroll').inert=false;$('#toggle-ai').setAttribute('aria-expanded','false');$('#toggle-ai').textContent='问问 AI';}
 const oldKey='study-ai-draft:'+state.article.article.id,legacyDraft=localStorage.getItem(oldKey);if(legacyDraft){const sid=state.article.sessions?.find(x=>x.legacy)?.id||state.article.session_id;const key=aiDraftKey(state.article.article.id,sid);if(!localStorage.getItem(key))localStorage.setItem(key,legacyDraft);localStorage.removeItem(oldKey);}localStorage.setItem('study-active-session:'+state.article.article.id,state.article.session_id);$('#ai-sessions').hidden=true;$('#history-ai').setAttribute('aria-expanded','false');
 let draft={};try{draft=JSON.parse(localStorage.getItem(aiDraftKey(state.article.article.id))||'{}');}catch{}
 aiSectionIndex=Number.isInteger(draft.section_index)?draft.section_index:state.article.chats.at(-1)?.section_index??null;aiQuote=typeof draft.quote==='string'?draft.quote:'';$('#ask-input').value=typeof draft.question==='string'?draft.question:'';aiPaintQuote();$('#ai-error').hidden=true;paintChat();
}
function aiReadingAnchor(){const root=$('#reader-scroll'),top=root.getBoundingClientRect().top;const node=[...root.querySelectorAll('h1,h2,h3,p,li,pre')].find(n=>n.getBoundingClientRect().bottom>top+20&&n.getBoundingClientRect().top<root.getBoundingClientRect().bottom);return node?{node,offset:node.getBoundingClientRect().top-top,atTop:root.scrollTop<1}:null;}
function aiRestoreReading(anchor){if(anchor?.node.isConnected){const root=$('#reader-scroll');root.scrollTo({top:anchor.atTop?0:root.scrollTop+anchor.node.getBoundingClientRect().top-root.getBoundingClientRect().top-anchor.offset,behavior:'instant'});}}
function openAI(quote,sectionIndex){
 if(!state.article)return;const anchor=aiReadingAnchor();
 if(!$('#reader').classList.contains('ai-open'))aiReturnFocus=document.activeElement;
 if(typeof quote==='string'){aiSectionIndex=Number.isInteger(sectionIndex)?sectionIndex:aiVisibleSection();aiQuote=quote;$('#ask-input').value='请用一个简单例子解释这段内容。';aiSaveDraft();}
 if(aiSectionIndex===null)aiSectionIndex=aiVisibleSection();$('#ai-drawer').hidden=false;$('#reader').classList.add('ai-open');$('#toggle-ai').setAttribute('aria-expanded','true');$('#toggle-ai').textContent='关闭 AI';$('#selection-menu').hidden=true;aiSyncViewport();aiRestoreReading(anchor);aiPaintQuote();paintChat();$('#ask-input').focus({preventScroll:true});
}
function expandAI(){openAI();}
function closeAI(restoreFocus=true){
 if(!state.article)return;const anchor=aiReadingAnchor();aiSaveDraft();$('#reader').classList.remove('ai-open');$('#ai-drawer').hidden=true;$('#reader-scroll').inert=false;$('#toggle-ai').setAttribute('aria-expanded','false');$('#toggle-ai').textContent='问问 AI';aiRestoreReading(anchor);
 if(restoreFocus){if(aiReturnFocus?.isConnected&&aiReturnFocus!==document.body&&!aiReturnFocus.closest('#ai-drawer')&&!aiReturnFocus.closest('#selection-menu'))aiReturnFocus.focus({preventScroll:true});else $('#toggle-ai').focus({preventScroll:true});}
}
function paintChat(){
 if(!state.article)return;const chats=state.article.chats,pending=aiPending.get(aiSessionKey(state.article.article.id,state.article.session_id));
 $('#chat-list').innerHTML=chats.map(c=>`<div class="chat-message user"><span class="speaker">你</span>${c.quote?`<blockquote>${esc(c.quote)}</blockquote>`:''}<div class="message-content">${esc(c.question)}</div></div><div class="chat-message assistant"><span class="speaker"><i aria-hidden="true">✧</i> 学习助手</span><div class="message-content">${markdown(c.reply)}</div></div>`).join('')+
 (pending?`<div class="chat-message user"><span class="speaker">你</span><div class="message-content">${esc(pending.question)}</div></div><div class="ai-thinking" role="status"><span class="thinking-dot"></span>正在结合原文整理回答…<small>你可以继续阅读，回答会保存在这篇文章里。</small></div>`:'')+
 (!chats.length&&!pending?(aiQuote?'<p class="ai-selection-hint">已带入选中的原文。直接发送，或补充你想弄懂的问题。</p>':`<div class="ai-welcome"><div class="ai-welcome-symbol" aria-hidden="true">✧</div><h2>新对话</h2><p>输入问题，或选中文字后提问。</p></div>`):'');
 $('#ask-button').disabled=!!pending;$('#ask-button').textContent=pending?'正在回答…':'发送问题';$('#ai-quick-prompts').hidden=!!pending;$('#chat-list').scrollTop=chats.length||pending?$('#chat-list').scrollHeight:0;
}
$('#toggle-ai').onclick=()=>$('#reader').classList.contains('ai-open')?closeAI():openAI();
$('#close-ai').onclick=()=>closeAI();
$('#clear-quote').onclick=()=>{aiQuote='';aiPaintQuote();aiSaveDraft();};
$('#ask-input').addEventListener('input',aiSaveDraft);
$('#ask-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();$('#ask-form').requestSubmit();}});
$('#ai-quick-prompts').onclick=e=>{const b=e.target.closest('[data-ai-prompt]');if(!b)return;$('#ask-input').value=b.dataset.aiPrompt;aiSaveDraft();$('#ask-input').focus();};
window.addEventListener('resize',aiSyncViewport);
$('#ask-form').onsubmit=async e=>{
 e.preventDefault();if(!state.article)return;const id=state.article.article.id,sid=state.article.session_id,key=aiSessionKey(id,sid),question=$('#ask-input').value.trim(),quote=aiQuote;if(!question){$('#ask-input').focus();return;}if(aiPending.has(key))return;
 aiSaveDraft();aiPending.set(key,{question,quote});$('#ai-error').hidden=true;paintChat();
 try{
  const chat=await api('/api/ai/ask',{article_id:id,question,quote,section_index:aiSectionIndex,session_id:sid});
  // Only clear the submitted draft. Preserve text the user typed while waiting.
  let saved={};try{saved=JSON.parse(localStorage.getItem(aiDraftKey(id,sid))||'{}');}catch{}
  if(saved.question?.trim()===question&&saved.quote===quote)localStorage.removeItem(aiDraftKey(id,sid));
  if(state.article?.article.id===id&&state.article.session_id===sid){if(!state.article.chats.some(c=>c.created===chat.created&&c.question===chat.question))state.article.chats.push(chat);if($('#ask-input').value.trim()===question&&aiQuote===quote){$('#ask-input').value='';aiQuote='';aiPaintQuote();}}
 }catch(err){if(state.article?.article.id===id&&state.article.session_id===sid){$('#ai-error').textContent=err.message+'。问题草稿已保留，可以再次发送。';$('#ai-error').hidden=false;}}
 finally{aiPending.delete(key);if(state.article?.article.id===id&&state.article.session_id===sid)paintChat();}
};

function aiSessionDate(value){return String(value||'').slice(0,16).replace('T',' ');}
function paintAISessions(rows){$('#ai-session-list').innerHTML=rows.map(x=>'<button class="ai-session-row '+(x.id===state.article.session_id?'current':'')+'" data-session-id="'+esc(x.id)+'"><span><strong>'+esc(x.title)+'</strong><small>'+esc(aiSessionDate(x.created))+' · '+x.count+' 轮</small></span><span>'+(x.id===state.article.session_id?'当前':'打开')+'</span></button>').join('')||'<p>还没有会话</p>';}
async function aiSelectSession(sid){if(!state.article)return;aiSaveDraft();const aid=state.article.article.id,request=++aiSessionSwitch;try{const chats=await api('/api/chats?article_id='+encodeURIComponent(aid)+'&session_id='+encodeURIComponent(sid));if(request!==aiSessionSwitch||state.article?.article.id!==aid)return;state.article.session_id=sid;state.article.chats=chats;resetAIForArticle(true);openAI();}catch(e){toast(e.message);}}
$('#history-ai').onclick=async()=>{const panel=$('#ai-sessions');if(!panel.hidden){panel.hidden=true;$('#history-ai').setAttribute('aria-expanded','false');return;}try{const aid=state.article.article.id,rows=await api('/api/chat/sessions?article_id='+encodeURIComponent(aid));if(state.article?.article.id!==aid)return;state.article.sessions=rows;paintAISessions(rows);panel.hidden=false;$('#history-ai').setAttribute('aria-expanded','true');}catch(e){toast(e.message);}};
$('#ai-session-list').onclick=e=>{const b=e.target.closest('[data-session-id]');if(b)aiSelectSession(b.dataset.sessionId);};
$('#new-ai').onclick=async e=>{if(!state.article)return;aiSaveDraft();const aid=state.article.article.id,request=++aiSessionSwitch,done=busyButton(e.currentTarget,'新建中…');try{const data=await api('/api/chat/new',{article_id:aid});if(request!==aiSessionSwitch||state.article?.article.id!==aid)return;Object.assign(state.article,data);resetAIForArticle(true);openAI();toast('已开启新对话，旧会话保留在历史中');}catch(err){toast(err.message);}finally{done();}};
