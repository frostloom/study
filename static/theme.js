// Apply before paint. This preference belongs to this browser, not study progress.
(()=>{const allowed=['white','dark','paper'];let current='white';try{const saved=localStorage.getItem('study-theme');if(allowed.includes(saved))current=saved;}catch{}
 const apply=value=>{current=allowed.includes(value)?value:'white';document.documentElement.dataset.theme=current;document.querySelectorAll('[data-theme-select]').forEach(s=>s.value=current);};apply(current);
 document.addEventListener('DOMContentLoaded',()=>{apply(current);document.querySelectorAll('[data-theme-select]').forEach(s=>s.addEventListener('change',()=>{apply(s.value);try{localStorage.setItem('study-theme',current);}catch{}}));});})();
