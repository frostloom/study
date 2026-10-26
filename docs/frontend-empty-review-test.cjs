const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/app.js','utf8').replace(/\r\n/g,'\n'),fn=source.match(/async function renderReview\(\)\{[\s\S]*?\n\}\n/)[0];
const nodes=new Map(),get=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'',addEventListener(){}});return nodes.get(s)};
const ctx={state:{view:'review',day:'2026-10-26',questionIndex:0},api:async p=>p.startsWith('/api/review')?{questions:[],status:'待作答'}:{completed:[],review_minutes:10},$:get,heading:()=>'',reviewMinutes:()=>10,esc:String,document:{querySelectorAll:()=>[]},localStorage:{getItem:()=>null}};
vm.createContext(ctx);vm.runInContext(fn,ctx);
(async()=>{await vm.runInContext('renderReview()',ctx);assert(get('#page').innerHTML.includes('id="start-review"'));console.log('empty reconciled review shows generation controls passed')})().catch(e=>{console.error(e);process.exit(1)});
