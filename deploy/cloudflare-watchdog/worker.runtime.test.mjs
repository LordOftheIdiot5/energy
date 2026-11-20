import test from "node:test";
import assert from "node:assert/strict";
import {fileURLToPath} from "node:url";
import {Miniflare,createFetchMock} from "miniflare";
const fixture=fileURLToPath(new URL("./runtime-fixture.mjs",import.meta.url));
const github="/repos/LordOftheIdiot5/energy/actions/workflows/fetch.yml";
const snapshot=(age)=>JSON.stringify({generated:new Date(Date.now()-age*60000).toISOString(),zones:[{}],europe:[]});
const jsonHeaders={"content-type":"application/json"};
test("workerd Durable Object: real fetch Request construction, recovery dispatch, Telegram and healthy reset",async()=>{
  const mock=createFetchMock();mock.disableNetConnect();
  const energy=mock.get("https://energy.nordl.dev");
  energy.intercept({path:"/data/energy.json",method:"GET"}).reply(200,snapshot(121),{headers:jsonHeaders});
  energy.intercept({path:"/data/energy.json",method:"GET"}).reply(200,snapshot(12),{headers:jsonHeaders});
  const gh=mock.get("https://api.github.com");
  for(const status of ["queued","in_progress","pending","waiting","requested"])gh.intercept({path:github+"/runs?branch=main&status="+status+"&per_page=1",method:"GET"}).reply(200,'{"total_count":0}',{headers:jsonHeaders});
  gh.intercept({path:github+"/dispatches",method:"POST"}).reply(204,"");
  const telegram=mock.get("https://api.telegram.org");
  telegram.intercept({path:"/botTESTONLY/sendMessage",method:"POST"}).reply(200,'{"ok":true}',{headers:jsonHeaders}).times(2);
  const mf=new Miniflare({modules:true,scriptPath:fixture,compatibilityDate:"2026-11-20",durableObjects:{WATCHDOG:{className:"Watchdog",useSQLite:true}},bindings:{GITHUB_DISPATCH_TOKEN:"TESTONLY",TELEGRAM_BOT_TOKEN:"TESTONLY",TELEGRAM_CHAT_ID:"TESTONLY"},fetchMock:mock});
  try{
    const first=await mf.dispatchFetch("http://localhost/tick");assert.equal(first.status,200);const a=await first.json();assert.equal(a.action,"dispatch-accepted");assert.equal(a.alertOpen,true);assert.deepEqual(a.diagnostics,{});
    const second=await mf.dispatchFetch("http://localhost/tick");assert.equal(second.status,200);const b=await second.json();assert.equal(b.failures,0);assert.equal(b.alertOpen,false);assert.deepEqual(b.diagnostics,{});assert.ok(b.age>=12&&b.age<70);mock.assertNoPendingInterceptors();
  }finally{await mf.dispose();await mock.close();}
});
test("workerd rejects external redirects without following them",async()=>{
  const mock=createFetchMock();mock.disableNetConnect();
  mock.get("https://energy.nordl.dev").intercept({path:"/data/energy.json",method:"GET"}).reply(302,"",{headers:{location:"https://example.invalid/never-follow"}});
  const mf=new Miniflare({modules:true,scriptPath:fixture,compatibilityDate:"2026-11-20",durableObjects:{WATCHDOG:{className:"Watchdog",useSQLite:true}},fetchMock:mock});
  try{const r=await mf.dispatchFetch("http://localhost/tick");assert.equal(r.status,200);const d=await r.json();assert.equal(d.failures,1);assert.equal(d.diagnostics.snapshot,"redirect-http-302");assert.equal(d.action,"none");mock.assertNoPendingInterceptors();}finally{await mf.dispose();await mock.close();}
});
