document.querySelector('#export').onclick=()=>{
 const items={};
 for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k==='study-theme'||['study-draft:','study-ai-draft:','study-active-session:'].some(p=>k.startsWith(p)))items[k]=localStorage.getItem(k);}
 const blob=new Blob([JSON.stringify(items)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='study-browser-preferences.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);document.querySelector('#status').textContent='已导出 '+Object.keys(items).length+' 项学习偏好和草稿。';
};
