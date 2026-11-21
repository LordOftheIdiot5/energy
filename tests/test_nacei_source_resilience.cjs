const assert=require('node:assert/strict'),fs=require('node:fs');
const {validate,reviewedArchive}=require('../atlas-nacei-oilgas.js');
const fixture=JSON.parse(fs.readFileSync('data/nacei-oilgas-2017-v1.json','utf8'));
assert.equal(validate(fixture),fixture);
const good={ok:true,status:200,json:async()=>fixture};
const http=status=>({ok:false,status,json:async()=>{throw Error('must not parse HTTP failure');}});
const pauses=[];
const pause=async ms=>{pauses.push(ms);};
const quick=[40,40,40];
(async()=>{
 let called=0,notes=[];
 let result=await reviewedArchive({
  fetcher:async(path,opt)=>{called++;assert.equal(path,'data/nacei-oilgas-2017-v1.json');assert.equal(opt.cache,'no-cache');assert.ok(opt.signal);return called===1?http(503):good;},
  pause,limits:quick,onProgress:s=>notes.push(s)
 });
 assert.equal(called,2);assert.equal(result.doc,fixture);assert.equal(result.attempt,2);
 assert.deepEqual(notes.map(x=>x.state),['loading','retrying','loading']);
 assert.equal(notes[1].reason,'http-503');assert.deepEqual(pauses,[250]);
 
 called=0;notes=[];
 result=await reviewedArchive({
  fetcher:async()=>{called++;if(called===1)throw new TypeError('offline');return good;},
  pause,limits:quick,onProgress:s=>notes.push(s)
 });
 assert.equal(result.attempt,2);assert.equal(notes[1].reason,'network');
 
 called=0;notes=[];
 result=await reviewedArchive({
  fetcher:async()=>{called++;return called===1?http(429):good;},
  pause,limits:quick,onProgress:s=>notes.push(s)
 });
 assert.equal(result.attempt,2);assert.equal(notes[1].reason,'http-429');

 called=0;
 const controllers=[];
 result=await reviewedArchive({
  fetcher:async(path,opt)=>{called++;controllers.push(opt.signal);return called===1?new Promise(()=>{}):good;},
  pause,limits:[20,40,40]
 });
 assert.equal(result.attempt,2,'Hanging initial request must time out and retry');
 assert.equal(controllers[0].aborted,true,'Timed-out request must be aborted');
 assert.equal(controllers[1].aborted,false);
 
 called=0;notes=[];
 await assert.rejects(reviewedArchive({
  fetcher:async()=>{called++;return http(503);},
  pause,limits:quick,onProgress:s=>notes.push(s)
 }),e=>e.reason==='http-503'&&e.retryable&&e.attempt===3);
 assert.equal(called,3,'Bounded 5xx retries');
 assert.equal(notes.filter(x=>x.state==='retrying').length,2);

 called=0;
 await assert.rejects(reviewedArchive({
  fetcher:async()=>{called++;return http(404);},
  pause,limits:quick
 }),e=>e.reason==='http-404'&&!e.retryable&&e.attempt===1);
 assert.equal(called,1,'4xx non-transient failures must not retry');

 called=0;
 await assert.rejects(reviewedArchive({
  fetcher:async()=>{called++;return {ok:true,json:async()=>({...fixture,source_period:'2026-11'})};},
  pause,limits:quick
 }),e=>e.reason==='invalid-provenance'&&!e.retryable&&e.attempt===1);
 assert.equal(called,1,'Wrong source/vintage/rights must fail closed without retry');

 called=0;
 await assert.rejects(reviewedArchive({
  fetcher:async()=>{called++;return {ok:true,json:async()=>{throw Error('bad json');}};},
  pause,limits:quick
 }),e=>e.reason==='invalid-json'&&!e.retryable&&e.attempt===1);
 assert.equal(called,1,'Malformed JSON must fail closed without retry');

 console.log('PASS NACEI approved-only recovery: one/two transient HTTP errors, request timeout + AbortController, network error, no 404/invalid-rights retry, bounded 3 attempts, original 1,461 source records');
})().catch(e=>{console.error(e);process.exitCode=1;});
