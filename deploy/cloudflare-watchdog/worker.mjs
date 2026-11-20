// Independent watchdog. No public control endpoint; no credentials in source.
const SNAPSHOT="https://energy.nordl.dev/data/energy.json";
const RUNS="https://api.github.com/repos/LordOftheIdiot5/energy/actions/workflows/fetch.yml";
const MIN=60000, MAX=2_000_000;
const active=["queued","in_progress","pending","waiting","requested"];
async function request(url,init={},fetcher=fetch){
  return fetcher(url,{...init,redirect:"error",signal:AbortSignal.timeout(7000)});
}
async function json(response,limit=MAX){
  if(!response.ok)throw Error("HTTP "+response.status);
  let n=0;const chunks=[],reader=response.body.getReader();
  try{while(true){const {value,done}=await reader.read();if(done)break;n+=value.byteLength;if(n>limit)throw Error("response limit");chunks.push(value);}}
  catch(e){await reader.cancel().catch(()=>{});throw e;}
  const b=new Uint8Array(n);let pos=0;for(const c of chunks){b.set(c,pos);pos+=c.length;}return JSON.parse(new TextDecoder().decode(b));
}
export async function probe(fetcher=fetch,now=Date.now()){
  const r=await request(SNAPSHOT,{cache:"no-store",headers:{"Cache-Control":"no-cache"},cf:{cacheTtl:0,cacheEverything:false}},fetcher);
  const d=await json(r),t=Date.parse(d.generated);
  if(!Number.isFinite(t)||t>now||!Array.isArray(d.zones)||!d.zones.length||!Array.isArray(d.europe))throw Error("invalid snapshot");
  return Math.floor((now-t)/MIN);
}
async function github(env,path,init={},fetcher=fetch){
  if(!env.GITHUB_DISPATCH_TOKEN)throw Error("missing GitHub secret");
  const r=await request(RUNS+path,{...init,headers:{"Authorization":"Bearer "+env.GITHUB_DISPATCH_TOKEN,"Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"Nordl-energy-watchdog"}},fetcher);
  if(!r.ok)throw Error("GitHub HTTP "+r.status);
  return r;
}
export async function recover(env,fetcher=fetch){
  // Fail closed if any active-state read fails. Workflow concurrency handles check/dispatch races.
  for(const status of active){
    const d=await json(await github(env,"/runs?branch=main&status="+status+"&per_page=1",{},fetcher));
    if(!Number.isInteger(d.total_count)||d.total_count<0)throw Error("invalid run count");
    if(d.total_count>0)return "already-active";
  }
  const r=await github(env,"/dispatches",{method:"POST",body:JSON.stringify({ref:"main",inputs:{recovery:"true"}})},fetcher);
  if(![200,204].includes(r.status))throw Error("unexpected dispatch reply");
  return "dispatch-accepted";
}
async function notify(env,message,fetcher=fetch){
  if(!env.TELEGRAM_BOT_TOKEN||!env.TELEGRAM_CHAT_ID)throw Error("missing Telegram secrets");
  const r=await request("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat_id:env.TELEGRAM_CHAT_ID,text:message,disable_web_page_preview:true})},fetcher);
  if(!(await json(r,100_000)).ok)throw Error("Telegram rejected notification");
}
export async function tick(state,io,now=Date.now()){
  let age=null;try{age=await io.probe();}catch{}
  state.failures=age===null?(state.failures||0)+1:0;
  const unhealthy=age===null?state.failures>=2:age>=110;
  const shouldRecover=age===null?state.failures>=2:age>=90;
  const healthy=age!==null&&age<70;
  let action="none";
  if(shouldRecover&&(!state.lastAttempt||now-state.lastAttempt>=30*MIN)){
    state.lastAttempt=now;await io.save(state);
    try{action=await io.recover();}catch{action="recovery-check-failed";}
  }
  if(unhealthy&&(!state.alertOpen||now-(state.lastAlert||0)>=120*MIN)){
    try{await io.notify("Nordl Energy freshness alert: "+(age===null?"public snapshot unavailable after repeated checks":age+" min since snapshot generation")+". Recovery: "+action+". https://energy.nordl.dev/");state.alertOpen=true;state.lastAlert=now;}catch{action+="; notification-failed";}
  }else if(healthy&&state.alertOpen){
    try{await io.notify("Nordl Energy recovered: public snapshot is "+age+" min old. https://energy.nordl.dev/");state.alertOpen=false;}catch{action+="; notification-failed";}
  }
  await io.save(state);
  return {age,failures:state.failures,action,alertOpen:!!state.alertOpen};
}
export class Watchdog{
  constructor(state,env){this.state=state;this.env=env;this.busy=false;}
  async fetch(req){
    if(req.method!=="POST")return new Response("Not found",{status:404});
    if(this.busy)return Response.json({action:"already-checking"});
    this.busy=true;
    try{
      const saved=await this.state.storage.get("state")||{};
      const result=await tick(saved,{probe:()=>probe(),recover:()=>recover(this.env),notify:m=>notify(this.env,m),save:s=>this.state.storage.put("state",s)});
      console.log("Nordl watchdog",JSON.stringify(result));
      return Response.json(result);
    }finally{this.busy=false;}
  }
}
export default{
  fetch(){return new Response("Not found",{status:404});},
  async scheduled(controller,env,ctx){
    const stub=env.WATCHDOG.get(env.WATCHDOG.idFromName("energy-production"));
    const r=await stub.fetch("https://watchdog.internal/tick",{method:"POST"});
    if(!r.ok)throw Error("Watchdog execution failed");
    const result=await r.json();
    if(result.action?.includes("failed"))throw Error("Watchdog action failed; check restricted logs");
  }
};
