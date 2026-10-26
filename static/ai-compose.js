/* Composer keyboard semantics and image encoding shared by the AI drawer. */
(function(){
'use strict';
function bindInput(input,{send,clear}){
 let composing=false,endTimer;input.addEventListener('compositionstart',()=>{clearTimeout(endTimer);composing=true;});input.addEventListener('compositionend',()=>{endTimer=setTimeout(()=>composing=false,0);});
 input.addEventListener('keydown',e=>{
  if(composing||e.isComposing||e.keyCode===229)return;
  if(e.key==='Backspace'&&e.shiftKey&&(e.metaKey||e.ctrlKey)){e.preventDefault();clear();return;}
  if(e.key==='Enter'&&!e.shiftKey&&!e.altKey){e.preventDefault();if(!e.repeat)send();}
 });
}
async function rasterizeImage(item){
 const img=new Image();await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{img.src='';reject(new Error('图片解码超时，请重试或选择仅文字'));},15000);img.onload=()=>{clearTimeout(timer);resolve();};img.onerror=()=>{clearTimeout(timer);reject(new Error('当前小节有图片未能解码，请重试或选择仅文字'));};img.src=item.data_url;});
 if(!img.naturalWidth||!img.naturalHeight)throw new Error('图片没有有效尺寸');
 const svg=item.data_url.startsWith('data:image/svg+xml');let width=img.naturalWidth,height=img.naturalHeight;
 if(svg){try{const xml=new TextDecoder().decode(Uint8Array.from(atob(item.data_url.split(',')[1]),c=>c.charCodeAt(0))),root=new DOMParser().parseFromString(xml,'image/svg+xml').documentElement,view=(root.getAttribute('viewBox')||'').trim().split(/[ ,]+/).map(Number);if(view.length===4&&Number.isFinite(view[2])&&Number.isFinite(view[3])&&view[2]>0&&view[3]>0){width=view[2];height=view[3];}}catch{}}
 const scale=Math.min(svg?2:1,2048/width,2048/height);
 const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale));
 const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
 let data=canvas.toDataURL('image/png');if(data.length>1572864)data=canvas.toDataURL('image/jpeg',.8);if(data.length>1572864)data=canvas.toDataURL('image/jpeg',.6);
 if(data.length>1572864)throw new Error('图片过大，请选更细的小节或选择仅文字');
 return {data_url:data,source_id:item.source_id,alt:item.alt||''};
}
window.AICompose={bindInput,prepareImages:images=>Promise.all(images.map(rasterizeImage))};
})();
