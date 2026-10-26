const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 const nodes=new Map();function el(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,hidden:false,isConnected:true,textContent:'',innerHTML:'',events:{},addEventListener(n,f){this.events[n]=f;},focus(){},insertAdjacentHTML(){}});return nodes.get(id);}
 let saved={onboarding_completed:true,goal:'old goal',topics:[],daily_minutes:60,review_minutes:15};
 let releaseDraft;let blockDraft=false;
 const ctx={window:{scrollTo(){}},setTimeout,clearTimeout,location:{hash:''},state:{view:'settings',catalog:[],status:{}},go:async()=>{},document:{querySelector:el,querySelectorAll:()=>[],body:{classList:{add(){},remove(){}}}},api:async(path,data)=>{if(path==='/api/setup/draft'){if(blockDraft)await new Promise(resolve=>releaseDraft=resolve);saved={...data.profile};return saved;}if(path==='/api/setup')return {profile:{...saved},model:{model:'test-model',ready:true}};throw Error(path);}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/release-ui.js','utf8'),ctx);const ui=ctx.window.ReleaseUI;
 await ui.start({profile:{...saved},model:{model:'test-model',ready:true}});await ui.showWizard(1);
 el('#release-goal').value='edited goal';el('#release-goal').events.input();
 blockDraft=true;const rendering=ui.renderSettings();await new Promise(r=>setTimeout(r,0));
 blockDraft=false;releaseDraft?.();await rendering;
 assert.equal(ctx.state.profile.goal,'edited goal','reopening settings flushes a pending edit before fetching profile');
 await new Promise(r=>setTimeout(r,400));assert.equal(saved.goal,'edited goal','a delayed autosave cannot overwrite the edit with a stale settings snapshot');
 console.log('settings autosave race passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
