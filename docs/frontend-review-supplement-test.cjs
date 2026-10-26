const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/app.js','utf8').replace(/\r\n/g,'\n'),fn=source.match(/async function renderReview\(\)\{[\s\S]*?\n\}\n/)[0];
const question=id=>({id,question:'question '+id,article_ids:['a'],answer:'',grade:null});
async function scenario(mode){
 const old={questions:[question('old1'),question('old2')]},updated={questions:[...old.questions,question('new1'),question('new2')]};let current=old,posts=0,reads=0,payload=null;const notices=[],nodes=new Map();
 const get=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'',addEventListener(){}});return nodes.get(s)};
 const ctx={state:{view:'review',day:'2026-10-26',questionIndex:1,catalog:[{id:'a',topic:'Go',title:'test'}]},api:async(path,body)=>{if(path==='/api/ai/review'){posts++;payload=body;if(mode==='error')throw Error('model failed');if(mode==='new')current=updated;if(mode==='leave'){current=updated;ctx.state.view='today'}return current;}if(path.startsWith('/api/review')){reads++;return current;}return {completed:[{id:'a'}],review_minutes:60}},$:get,heading:()=>'',reviewMinutes:()=>60,esc:String,document:{querySelectorAll:()=>[]},localStorage:{getItem:()=>null,setItem(){}},toast:m=>notices.push(m),busyButton:()=>()=>{}};
 vm.createContext(ctx);vm.runInContext(fn,ctx);await ctx.renderReview();const beforeReads=reads;get('#review-answer').value='unsent draft';await get('#supplement-review').onclick({currentTarget:{}});
 assert.equal(posts,1);assert.equal(payload.additional,true,'manual button must request extra questions for existing reading');
 if(mode==='none'){assert(notices.length,'no new content must produce visible feedback');assert.equal(reads,beforeReads,'no new questions should not redraw an active answer');assert.equal(ctx.state.questionIndex,1);assert.equal(get('#review-answer').value,'unsent draft');}
 if(mode==='new'){assert.equal(ctx.state.questionIndex,2,'jump to the first newly added question');assert(get('#page').innerHTML.includes('question new1'));assert(notices.some(m=>m.includes('2')),'report count of added questions');assert.equal(old.questions.length,2);}
 if(mode==='error'){assert(notices.some(m=>m.includes('model failed')));assert.equal(ctx.state.questionIndex,1);}
 if(mode==='leave'){assert.equal(ctx.state.questionIndex,1,'response for a closed review should not change current navigation');assert.equal(reads,beforeReads);}
}
(async()=>{for(const mode of ['none','new','error','leave'])await scenario(mode);console.log('review supplement feedback, new-question navigation, errors and view isolation passed')})().catch(e=>{console.error(e);process.exit(1)});
