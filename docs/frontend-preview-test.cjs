const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 const nodes=new Map(),calls=[];function node(s){if(!nodes.has(s))nodes.set(s,{isConnected:true,disabled:false,textContent:'',hidden:true,focus(){},remove(){nodes.delete(s);}});return nodes.get(s);}
 const ctx={window:{},URL,setTimeout,clearTimeout,state:{catalog:[]},markdown:t=>t,DOMPurify:{sanitize:t=>t},document:{querySelector:node,createElement:()=>({setAttribute(){},addEventListener(){},showModal(){this.open=true;},close(){this.open=false;}}),body:{append(el){nodes.set('#'+el.id,el);}}},api:async(path,data)=>{calls.push({path,data});if(path==='/api/resources/preview')return {title:'Read me',url:data.url,text:'Actual article body',truncated:true};throw Error('Unexpected request '+path);}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/release-ui.js','utf8'),ctx);
 await ctx.window.ReleaseUI.previewURL('https://example.com/article',node('#preview-opener'));
 assert.deepEqual(calls.map(c=>c.path),['/api/resources/preview'],'preview fetch never imports or schedules the resource');
 const dialog=nodes.get('#release-preview');assert.equal(dialog.open,true);assert.ok(dialog.innerHTML.includes('Actual article body'),'preview displays returned article text');assert.ok(dialog.innerHTML.includes('加入阅读'),'import requires an explicit action');
 await ctx.window.ReleaseUI.previewURL('file:///etc/passwd',node('#preview-opener'));
 assert.equal(calls.length,1,'preview only allows HTTP(S) URLs');
 console.log('resource preview passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
