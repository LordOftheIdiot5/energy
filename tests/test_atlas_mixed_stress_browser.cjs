const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const BASE=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
const eia=JSON.parse(fs.readFileSync('data/eia860m-generators-v1.json','utf8'));
const positive=eia.rows.find(r=>r.coordinates[0]>0&&r.state&&r.id);
const SOURCES=['/data/uk-repd-projects-v1.json','/data/nacei-oilgas-2017-v1.json',
 '/data/gem-gas-202511/gem-gas-pipelines-202511-v1.json',
 '/data/gem-gas-202511/gem-gas-pipeline-routes-202511-v1.geojson'];
const wrapDistance=(a,b)=>Math.abs(((a-b+540)%360)-180);
async function captureHeap(cdp){
 const {usedSize,totalSize}=await cdp.send('Runtime.getHeapUsage');
 return {usedMiB:Math.round(usedSize/1048576*10)/10,allocatedMiB:Math.round(totalSize/1048576*10)/10};
}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
 for(const width of [1440,1024,390]){
  const page=await browser.newPage({viewport:{width,height:960}});
  const cdp=await page.context().newCDPSession(page),errors=[],requests=[],received=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{const u=new URL(r.url());if(u.pathname.startsWith('/data/'))requests.push(u.pathname);});
  page.on('response',r=>{
   const path=new URL(r.url()).pathname;
   if(path.startsWith('/data/'))received.push({path,status:r.status(),size:Number(r.headers()['content-length']||0)});
  });
  await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:65000});
  assert.ok(!SOURCES.some(path=>requests.includes(path)),'Atlas must not preload heavy disabled source files');
  const memStart=await captureHeap(cdp);
  await page.locator('#globalUkProjects').check();
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.ukRecords==='14388',null,{timeout:65000});
  await page.locator('#globalNaceiHistoric').check();
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.naceiRecords==='1278',null,{timeout:65000});
  await page.locator('#globalGemPipelines').check();
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRenderedFeatures==='3921',null,{timeout:65000});
  await page.locator('#globalUsGenerators').check();
  await page.locator('#usGeneratorInventory').selectOption('operating');
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.usRecords==='28712',null,{timeout:65000});
  await page.locator('#usGeneratorView').click();
  await page.waitForFunction(()=>Number(document.querySelector('#atlasMap').dataset.usMarkers)>0,null,{timeout:25000});
  await page.waitForTimeout(250);
  const memMixed=await captureHeap(cdp),snapshots=[];
  for(const [name,lng,lat,zoom] of [
   ['continental-us',-98,39,3],['britain',-2,54,4],['norway',12,62,4],
   ['western-dateline',179.4,43,3],['eastern-dateline',-179.4,43,3],
   ['north-america',-105,45,3],['global',0,15,1],
  ]){
   await page.evaluate(([x,y,z])=>{
    const m=window.NordlEnergyAtlas.getMap();m.jumpTo({center:[x,y],zoom:z,bearing:0,pitch:0});
   },[lng,lat,zoom]);
   await page.waitForTimeout(180);
   const state=await page.evaluate(()=>{
    const el=document.querySelector('#atlasMap'),m=window.NordlEnergyAtlas.getMap();
    return {center:[m.getCenter().lng,m.getCenter().lat],zoom:m.getZoom(),
      gemRecords:Number(el.dataset.gemRecords),routes:Number(el.dataset.gemRenderedFeatures),
      ukRecords:Number(el.dataset.ukRecords),usRecords:Number(el.dataset.usRecords),
      naceiRecords:Number(el.dataset.naceiRecords),
      ukMarkers:Number(el.dataset.ukMarkers),usMarkers:Number(el.dataset.usMarkers),
      naceiMarkers:Number(el.dataset.naceiMarkers),
      visibleGem:m.getLayoutProperty('nordl-gem-gas-routes','visibility')||'visible',
      toggles:['globalUkProjects','globalUsGenerators','globalNaceiHistoric','globalGemPipelines'].every(id=>document.getElementById(id).checked)};
   });
   assert.ok(state.toggles,'All chosen overlays must remain enabled after '+name);
   assert.equal(state.gemRecords,2975);
   assert.equal(state.routes,3921,'Zoom must not discard original source-line coverage');
   assert.equal(state.ukRecords,14388);
   assert.equal(state.usRecords,28712);
   assert.equal(state.naceiRecords,1278);
   assert.equal(state.visibleGem,'visible');
   assert.ok(Number.isFinite(state.center[0])&&Number.isFinite(state.center[1]));
   console.log('V90.6g4b camera',width,name,JSON.stringify({requested:[lng,lat,zoom],actual:state.center,zoom:state.zoom,markers:[state.ukMarkers,state.usMarkers,state.naceiMarkers]}));
   assert.ok(wrapDistance(state.center[0],lng)<2,'Camera crossed to wrong longitude at '+name+': got '+state.center[0]+' wanted '+lng);
   assert.ok(state.ukMarkers>=0&&state.usMarkers>=0&&state.naceiMarkers>=0);
   assert.ok(state.ukMarkers+state.usMarkers+state.naceiMarkers<1500,'Unbounded DOM marker generation '+name);
   if(name==='continental-us'||name==='north-america')assert.ok(state.usMarkers>0&&state.naceiMarkers>0,'US and NACEI should be visible together');
   if(name==='britain')assert.ok(state.ukMarkers>0,'UK projects should reappear on country view');
   snapshots.push({name,zoom:state.zoom,uk:state.ukMarkers,us:state.usMarkers,nacei:state.naceiMarkers});
  }
  if(positive&&width===1440){
   // The exact EIA native ID has a positive longitude; it must not be dropped
   // by a US-centric negative-longitude bounds optimization.
   const controls=page.locator('#globalUsGenerators').locator('xpath=ancestor::div[contains(@class,"atlas-digital-controls")]');
   await controls.locator('details').evaluate(e=>e.open=true);
   await page.locator('#usGeneratorInventory').selectOption(positive.inventory);
   await page.waitForFunction(kind=>document.querySelector('#usGeneratorInventory').value===kind&&Number(document.querySelector('#atlasMap').dataset.usRecords)>0,positive.inventory,{timeout:65000});
   await page.locator('#usGeneratorState').selectOption(positive.state);
   await page.locator('#usGeneratorFind').fill(positive.id);
   await page.waitForFunction(id=>[...document.querySelector('#usGeneratorResults').options].some(o=>o.value===id),positive.id,{timeout:30000});
   await page.locator('#usGeneratorView').click();
   const state=await page.evaluate(()=>{
     const m=window.NordlEnergyAtlas.getMap();return {lng:m.getCenter().lng,zoom:m.getZoom(),bounds:window.NordlUsGenerators.getBounds()};
   });
   assert.ok(wrapDistance(state.lng,positive.coordinates[0])<2,'Territory source record excluded from US fit');
   assert.ok(state.bounds&&state.bounds[0][0]>0,'Positive longitude selected source must remain in view bounds');
   await page.locator('#usGeneratorFind').fill('');
   await page.locator('#usGeneratorState').selectOption('');
  }
  // Exercise all four original EIA unit inventories and verify a bounded
  // validated-source cache with no retained completed promises.
  if(width===1440){
   for(const [kind,n] of [['planned',2357],['operating',28712],['retired',7303],['canceled_postponed',1676]]){
    await page.locator('#usGeneratorInventory').selectOption(kind);
    await page.waitForFunction(([expected,which])=>document.querySelector('#atlasMap').dataset.usRecords===String(expected)&&
      document.querySelector('#usGeneratorStatus').textContent.toLowerCase().includes(which==='canceled_postponed'?'canceled':'units'),
      [n,kind],{timeout:65000});
    const c=await page.evaluate(()=>window.NordlUsGenerators.cacheStatus());
    assert.ok(c.cached.length<=2,'EIA validated partition cache must remain bounded');
   }
   await page.waitForFunction(()=>window.NordlUsGenerators.cacheStatus().pending.length===0,null,{timeout:30000});
   const recent=await page.evaluate(()=>window.NordlUsGenerators.cacheStatus());
   assert.deepEqual(recent.cached,['retired','canceled_postponed']);
  }
  const memFinal=await captureHeap(cdp);
  for(const path of SOURCES){
   assert.equal(requests.filter(x=>x===path).length,1,'Source should be requested only once in session: '+path);
  }
  assert.deepEqual(errors,[],'No page runtime errors at '+width);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4),'Responsive horizontal overflow '+width);
  const unexpected=received.filter(r=>r.status!==200&&SOURCES.includes(r.path));
  assert.deepEqual(unexpected,[],'Validated archives are missing in public staging');
  console.log('PASS V90.6g4b simultaneous Atlas '+width+'px',JSON.stringify({
   memStart,memMixed,memFinal,sourceRequests:requests.length,
   knownSourceBytes:received.reduce((a,r)=>a+(Number.isFinite(r.size)?r.size:0),0),
   observedCameraRegions:snapshots,positiveTerritoryRecord:positive?{id:positive.id,inventory:positive.inventory}:null,
   cache:await page.evaluate(()=>window.NordlUsGenerators.cacheStatus())
  }));
  await page.close();
 }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
