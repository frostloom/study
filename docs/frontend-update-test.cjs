const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync('static/updates.js','utf8');
async function run(channel,available){
 const button={hidden:true,textContent:'',onclick:null},label={textContent:''},nodes={'#app-update':button,'.sidebar-label':label},calls=[],intervals=[];
 const document={readyState:'complete',title:'Study',visibilityState:'visible',body:{classList:{add(x){nodes.preview=x}}},querySelector(s){return nodes[s]||null},addEventListener(){}};
 const ctx={document,fetch:async path=>{calls.push(path);return {ok:true,json:async()=>path==='/api/app'?{channel}:{available,version:'1.2.0',current_version:'1.1.0'}}},setInterval:(fn,ms)=>intervals.push({fn,ms})};
 vm.runInNewContext(code,ctx);await new Promise(resolve=>setImmediate(resolve));
 return {button,label,nodes,calls,intervals};
}
(async()=>{
 let x=await run('stable',true);assert.equal(x.button.hidden,false,'new release must appear without clicking check');assert.equal(typeof x.button.onclick,'function');assert.deepEqual(x.calls,['/api/app','/api/updates']);assert.equal(x.intervals[0].ms,21600000);await x.intervals[0].fn();assert.equal(x.calls.length,3);
 x=await run('stable',false);assert.equal(x.button.hidden,true,'no new version must remain quiet');
 x=await run('preview',true);assert.equal(x.button.hidden,true);assert.deepEqual(x.calls,['/api/app']);assert.equal(x.intervals.length,0);console.log('automatic update notification behavior passed');
})().catch(e=>{console.error(e);process.exit(1)});
