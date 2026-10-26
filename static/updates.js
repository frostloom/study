/* New versions announce themselves; checking is never a prerequisite for learning. */
(()=>{
'use strict';
let latest=null,checking=false;
const q=s=>document.querySelector(s);
function close(){q('#update-dialog')?.close();}
function show(){
 if(!latest?.available)return;
 q('#update-dialog')?.remove();
 const d=document.createElement('dialog');d.id='update-dialog';d.className='update-dialog';
 d.setAttribute('aria-labelledby','update-title');
 d.innerHTML='<header><h2 id="update-title"></h2><button class="ghost" id="update-close" aria-label="关闭更新说明">关闭</button></header><p id="update-version"></p><pre id="update-notes"></pre><p class="update-install-note">下载后退出应用并安装新版，学习资料和记录会继续保留。预览版与正式版的数据互相独立。</p><footer><a class="secondary" id="update-release" target="_blank" rel="noopener noreferrer">查看发布页</a><a class="primary" id="update-download" target="_blank" rel="noopener noreferrer">下载新版</a></footer>';
 document.body.append(d);q('#update-title').textContent='新版本 '+latest.version;
 q('#update-version').textContent='当前版本 '+latest.current_version;
 q('#update-notes').textContent=latest.notes||'完整更新内容请查看发布页。';
 q('#update-release').href=latest.release_url;q('#update-download').href=latest.download_url;
 q('#update-close').onclick=close;d.addEventListener('close',()=>d.remove());d.showModal();
}
function render(result){
 latest=result;
 const button=q('#app-update');if(!button)return;
 button.hidden=!result.available;
 if(result.available){button.textContent='有新版本，立即更新';button.title='更新至 '+result.version;button.onclick=show;}
}
async function check(){
 if(checking)return;checking=true;
 try{const r=await fetch('/api/updates');if(r.ok)render(await r.json());}catch{}finally{checking=false;}
}
async function init(){
 try{const r=await fetch('/api/app');if(r.ok){const info=await r.json();if(info.channel==='preview'){document.body.classList.add('preview-channel');const b=q('.sidebar-label');if(b)b.textContent='开发预览 · 独立数据';document.title='日常学习预览版';return;}}}catch{}
 await check();setInterval(check,6*60*60*1000);
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')check();});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
