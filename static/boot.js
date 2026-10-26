(async()=>{
 try{
  const r=await fetch('/api/browser-state');
  if(r.ok){const transfer=await r.json();if(transfer?.id&&transfer.items){
   for(const [k,v] of Object.entries(transfer.items))if(localStorage.getItem(k)===null)localStorage.setItem(k,v);
   const theme=localStorage.getItem('study-theme');if(['white','dark','paper'].includes(theme)){document.documentElement.dataset.theme=theme;document.querySelectorAll('[data-theme-select]').forEach(x=>x.value=theme);}
   await fetch('/api/browser-state/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:transfer.id})});
  }}
 }catch{}finally{init();}
})();
