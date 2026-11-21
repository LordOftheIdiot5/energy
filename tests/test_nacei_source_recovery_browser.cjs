const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const BASE=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
const NACEI='**/data/nacei-oilgas-2017-v1.json';
const fixture=JSON.parse(fs.readFileSync('data/nacei-oilgas-2017-v1.json','utf8'));
const ready=()=>document.getElementById('atlasMap').dataset.naceiSourceState==='ready'
 && document.getElementById('atlasMap').dataset.naceiRecords==='1278';
const unavailable=()=>document.getElementById('atlasMap').dataset.naceiSourceState==='unavailable';
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const width of [1440,390]){
   const page=await browser.newPage({viewport:{width,height:940}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   let requests=0;
   await page.route(NACEI,async route=>{
    requests++;
    if(requests===1)await route.fulfill({status:503,body:'transient unavailable'});
    else await route.continue();
   });
   await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
   assert.equal(requests,0,'Optional NACEI archive must not be preloaded');
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(ready,null,{timeout:60000});
   assert.equal(requests,2,'HTTP 503 must trigger exactly one bounded retry');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-source-attempt'),'2');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-source-reason'),'');
   assert.ok((await page.locator('#naceiStatus').innerText()).includes('August 2017'));
   await page.locator('#naceiView').click();
   await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.naceiMarkers)>0,null,{timeout:25000});
   const count=await page.locator('#atlasMap .atlas-nacei-marker').count();
   assert.ok(count>0&&count<800);
   await page.locator('#globalNaceiHistoric').uncheck();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.naceiMarkers==='0');
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(ready);
   assert.equal(requests,2,'Reviewed valid source must be cached through toggle');
   assert.deepEqual(errors,[],'No page errors at '+width);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4));
   console.log('PASS NACEI source recovery browser '+width+'px · single 503 then validated original 1,461 records, source attempt 2, no repeat on toggle, markers '+count);
   await page.close();
  }
  {
   const page=await browser.newPage({viewport:{width:1440,height:940}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   let requests=0,invalid=true;
   await page.route(NACEI,async route=>{
    requests++;
    if(invalid)await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...fixture,source_period:'2026-11'})});
    else await route.continue();
   });
   await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(unavailable,null,{timeout:15000});
   assert.equal(requests,1,'Unapproved source must not be retried');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-source-reason'),'invalid-provenance');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-records'),'0');
   assert.equal(await page.locator('#atlasMap .atlas-nacei-marker').count(),0);
   assert.ok((await page.locator('#naceiStatus').innerText()).includes('failed source validation'));
   // Inability to load the historic archive must not block a separate
   // already-reviewed global gas pipeline archive.
   await page.locator('#globalGemPipelines').check();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.gemRenderedFeatures==='3921',null,{timeout:60000});
   invalid=false;
   await page.locator('#globalNaceiHistoric').uncheck();
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(ready,null,{timeout:60000});
   assert.equal(requests,2,'Fresh reviewed source must recover by manual retry');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-gem-rendered-features'),'3921');
   assert.ok(await page.locator('#globalGemPipelines').isChecked());
   assert.deepEqual(errors,[]);
   console.log('PASS NACEI fail-closed browser · reject forged source period without retry, manual recover, independent GEM stays visible');
   await page.close();
  }
  {
   const page=await browser.newPage({viewport:{width:390,height:940}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   let failures=true,requests=0;
   await page.route(NACEI,async route=>{
    requests++;
    if(failures)await route.fulfill({status:503,body:'temporary'});
    else await route.continue();
   });
   await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(unavailable,null,{timeout:30000});
   assert.equal(requests,3,'No unbounded source outage requests');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-source-attempt'),'3');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-source-reason'),'http-503');
   assert.equal(await page.locator('#atlasMap').getAttribute('data-nacei-records'),'0');
   failures=false;
   await page.locator('#globalNaceiHistoric').uncheck();
   await page.locator('#globalNaceiHistoric').check();
   await page.waitForFunction(ready,null,{timeout:60000});
   assert.equal(requests,4);
   assert.deepEqual(errors,[]);
   console.log('PASS NACEI persistent 503 budget · exactly 3 requests, explicit historical unavailable status, successful manual recovery');
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
