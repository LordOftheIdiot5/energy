import test from "node:test";import assert from "node:assert/strict";import {tick,probe,recover} from "./worker.mjs";
const now=Date.parse("2026-11-20T12:00:00Z"), minute=60000;
function mock(age){const calls=[];const io={probe:async()=>{if(age===null)throw Error("offline");return age;},recover:async()=>{calls.push("recover");return "dispatch-accepted";},notify:async m=>calls.push(m),save:async()=>{}};return {io,calls};}
test("healthy probe skips collection and alerts",async()=>{const {io,calls}=mock(25);assert.equal((await tick({},io,now)).action,"none");assert.deepEqual(calls,[]);});
test("early recovery, cooldown, alert and recovery notification",async()=>{const state={};const a=mock(95);await tick(state,a.io,now);assert.deepEqual(a.calls,["recover"]);let b=mock(115);await tick(state,b.io,now+15*minute);assert.equal(b.calls.length,1);assert.match(b.calls[0],/115 min/);b=mock(130);await tick(state,b.io,now+30*minute);assert.deepEqual(b.calls,["recover"]);const c=mock(20);await tick(state,c.io,now+45*minute);assert.match(c.calls[0],/recovered/);assert.equal(state.alertOpen,false);});
test("first failed probe does not dispatch, repeat does",async()=>{const s={},a=mock(null);await tick(s,a.io,now);assert.equal(a.calls.length,0);await tick(s,a.io,now+15*minute);assert.equal(a.calls.length,2);});
test("invalid or future snapshots rejected",async()=>{const simulate=d=>async()=>Response.json(d);await assert.rejects(probe(simulate({generated:new Date(now+1000).toISOString(),zones:[{}],europe:[]}),now));assert.equal(await probe(simulate({generated:new Date(now-20*minute).toISOString(),zones:[{}],europe:[]}),now),20);});
test("active run and failed GitHub query never dispatch",async()=>{let calls=[];const f=async(url,init)=>{calls.push([url,init.method]);return Response.json({total_count:1});};assert.equal(await recover({GITHUB_DISPATCH_TOKEN:"test"},f),"already-active");assert.equal(calls.length,1);await assert.rejects(recover({GITHUB_DISPATCH_TOKEN:"test"},async()=>new Response("",{status:403})));});
test("guarded dispatch only after all active status checks",async()=>{const calls=[];const f=async(url,init)=>{calls.push([url,init]);return url.endsWith("/dispatches")?new Response(null,{status:204}):Response.json({total_count:0});};assert.equal(await recover({GITHUB_DISPATCH_TOKEN:"test"},f),"dispatch-accepted");assert.equal(calls.length,6);assert.deepEqual(JSON.parse(calls.at(-1)[1].body),{ref:"main",inputs:{recovery:"true"}});});
test("failed Telegram delivery is not recorded as sent",async()=>{const a=mock(120),state={};a.io.notify=async()=>{throw Error("test");};const result=await tick(state,a.io,now);assert.match(result.action,/notification-failed/);assert.equal(state.alertOpen,undefined);});

test("diagnostics identify failed stages and never emit raw error text",async()=>{const state={failures:1};const {io}=mock(null);io.probe=async()=>{throw new TypeError("SECRET URL");};io.recover=async()=>{throw Error("SECRET TOKEN");};io.notify=async()=>{throw Error("SECRET CHAT");};const result=await tick(state,io,now);assert.deepEqual(result.diagnostics,{snapshot:"runtime-type-error",github:"runtime-error",telegram:"runtime-error"});assert.doesNotMatch(JSON.stringify(result),/SECRET/);});
test("HTTP failures preserve only numeric status",async()=>{const state={failures:1};const {io}=mock(null);io.probe=()=>probe(async()=>new Response("private",{status:403}),now);io.recover=()=>recover({GITHUB_DISPATCH_TOKEN:"secret"},async()=>new Response("private",{status:401}));const result=await tick(state,io,now);assert.equal(result.diagnostics.snapshot,"http-403");assert.equal(result.diagnostics.github,"github-http-401");});
test("default global fetch is called with the owning global receiver",async()=>{const old=globalThis.fetch;try{globalThis.fetch=function(){assert.equal(this,globalThis);return Promise.resolve(Response.json({generated:new Date(now-60000).toISOString(),zones:[{}],europe:[]}));};assert.equal(await probe(undefined,now),1);}finally{globalThis.fetch=old;}});

test("all request paths use workerd-compatible manual redirects",async()=>{const f=async(url,init)=>{assert.equal(init.redirect,"manual");return url.endsWith("/dispatches")?new Response(null,{status:204}):Response.json({total_count:0});};assert.equal(await recover({GITHUB_DISPATCH_TOKEN:"test"},f),"dispatch-accepted");await probe(async(url,init)=>{assert.equal(init.redirect,"manual");return Response.json({generated:new Date(now-60000).toISOString(),zones:[{}],europe:[]});},now);});
test("redirects fail closed with safe diagnostics and no follow-up request",async()=>{let calls=0;const f=async()=>{calls++;return new Response("private",{status:302,headers:{Location:"https://example.invalid/SECRET"}});};await assert.rejects(probe(f,now),e=>e.code==="redirect-http-302");await assert.rejects(recover({GITHUB_DISPATCH_TOKEN:"test"},f),e=>e.code==="redirect-http-302");assert.equal(calls,2);});

test("runtime TypeError in probe does not trigger false recovery or outage alerts",async()=>{
  const calls=[];const state={failures:51,lastAttempt:0};
  const result=await tick(state,{probe:async()=>{throw new TypeError("WORKER INTERNAL PRIVATE URL");},recover:async()=>calls.push("recovery"),notify:async()=>calls.push("alert"),save:async()=>{}},now);
  assert.equal(result.action,"probe-unverified");
  assert.equal(result.failures,52);
  assert.deepEqual(calls,[]);
  assert.deepEqual(result.diagnostics,{snapshot:"runtime-type-error"});
  assert.doesNotMatch(JSON.stringify(result),/PRIVATE/);
});
test("snapshot probe uses simple request without nonportable cache extensions",async()=>{
  const calls=[];const fetcher=async(url,init)=>{calls.push(init);return Response.json({generated:new Date(now-5*minute).toISOString(),zones:[{}],europe:[]});};
  assert.equal(await probe(fetcher,now),5);assert.equal(calls.length,1);
  assert.equal(calls[0].cache,undefined);assert.equal(calls[0].cf,undefined);
  assert.equal(calls[0].redirect,"manual");
});
test("snapshot outgoing TypeError diagnosed separately and suppresses dispatch",async()=>{
  let recovered=0;const state={failures:51};
  const result=await tick(state,{probe:()=>probe(async()=>{throw new TypeError("PRIVATE");},now),recover:async()=>{recovered++},notify:async()=>{recovered++},save:async()=>{}},now);
  assert.equal(result.diagnostics.snapshot,"snapshot-fetch-type-error");assert.equal(recovered,0);assert.equal(result.action,"probe-unverified");
});
