import test from "node:test";
import assert from "node:assert/strict";
import {fileURLToPath} from "node:url";
import {readFileSync} from "node:fs";
import {Miniflare,convertV4MiniflareOptions} from "miniflare";
const fixture=fileURLToPath(new URL("./runtime-fixture.mjs",import.meta.url));
const worker=fileURLToPath(new URL("./worker.mjs",import.meta.url));
test("actual workerd Request construction for snapshot and guarded GitHub dispatch",async()=>{
 const mf=new Miniflare(convertV4MiniflareOptions({modules:[{type:"ESModule",path:fixture,contents:readFileSync(fixture,"utf8")},{type:"ESModule",path:worker,contents:readFileSync(worker,"utf8")}],compatibilityDate:"2026-11-20"}));
 try{
  const a=await (await mf.dispatchFetch("http://localhost/probe")).json();
  assert.equal(a.age,1);assert.equal(a.trace[0].redirect,"manual");
  assert.equal(a.trace[0].hasCache,false);assert.equal(a.trace[0].hasCf,false);
  const b=await (await mf.dispatchFetch("http://localhost/recover")).json();
  assert.equal(b.action,"dispatch-accepted");assert.equal(b.trace.length,6);
  assert.equal(b.trace[5].method,"POST");
  const c=await (await mf.dispatchFetch("http://localhost/redirect")).json();
  assert.equal(c.error,"redirect-http-302");assert.equal(c.trace.length,1);
 } finally {await mf.dispose();}
});
