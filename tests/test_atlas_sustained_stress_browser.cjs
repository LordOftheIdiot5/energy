// V90.6g4e: sustained, repeatable CI-level Atlas stress (not physical-device GPU FPS).
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const BASE=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
const PUB=process.env.ATLAS_PUBLIC_DIR;
if(!PUB)throw Error('ATLAS_PUBLIC_DIR must point to rights-allowlisted staged website');
const index=JSON.parse(fs.readFileSync(path.join(PUB,'data/atlas-tiles/index-v1.json'),'utf8'));
const archive=fs.readFileSync(path.join(PUB,'data/atlas-tiles',index.path));
const output='/tmp/atlas-v90g4e-stress';
fs.mkdirSync(output,{recursive:true});
const cameras=[
 [10,59,2],[-78,38,3],[104,31,3],[25,-16,3],
 [179.4,0,8],[-179.4,0,8],[-123,47,4],[8,61,4],
 [43,33,3],[133,-25,3],[-49,-12,3],[10,55,2]
];
function percentile(values,p){const a=values.slice().sort((x,y)=>x-y);return a.length?a[Math.floor((a.length-1)*p)]:null;}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{for(const width of [1440,1024,390]){
  const page=await browser.newPage({viewport:{width,height:930}});
  const errors=[],requests=[],responses=[];let ranges=0,rangeBytes=0;
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('requestfailed',r=>{const url=r.url();if(url.includes('/data/'))errors.push('dataset request failed '+url);});
  page.on('request',r=>{const pathname=new URL(r.url()).pathname;if(pathname.startsWith('/data/'))requests.push(pathname);});
  page.on('response',r=>{const pathname=new URL(r.url()).pathname;if(pathname.startsWith('/data/'))responses.push({pathname,status:r.status()});});
  await page.route('**/pmtiles@4.5.0/dist/pmtiles.js',r=>r.fulfill({path:require.resolve('pmtiles').replace(/dist.*$/,'dist/pmtiles.js'),contentType:'text/javascript'}));
  await page.route('**/data/atlas-tiles/*.pmtiles',async route=>{
   const match=/^bytes=(\d+)-(\d+)$/.exec(route.request().headers().range||'');
   if(!match){await route.fulfill({status:400,body:'Expected PMTiles byte range'});return;}
   const start=Number(match[1]),end=Math.min(Number(match[2]),archive.length-1);
   ranges++;rangeBytes+=end-start+1;
   await route.fulfill({status:206,headers:{'Content-Range':'bytes '+start+'-'+end+'/'+archive.length,'Content-Length':String(end-start+1),'Accept-Ranges':'bytes','ETag':'"atlas-stress"','Content-Type':'application/octet-stream'},body:archive.subarray(start,end+1)});
  });
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('HeapProfiler.enable');
  const readHeap=async()=>{await cdp.send('HeapProfiler.collectGarbage');await page.waitForTimeout(90);const h=await cdp.send('Runtime.getHeapUsage');return Math.round(h.usedSize/1048576*10)/10;};
  await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
  await page.locator('#globalWri').check();
  await page.locator('#atlasWorld').click();
  await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.globalAssetRecords)>30000&&Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols)>0,null,{timeout:60000});
  await page.locator('#globalGdw').check();
  await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.gdwAssetRecords==='41145',null,{timeout:60000});
  await page.locator('#globalGpu').check();
  await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='gpu-vector'&&Number(document.getElementById('atlasMap').dataset.gpuSymbols)>0,null,{timeout:60000});
  assert.ok(ranges>0,'Vector data must be sourced through verified PMTiles ranges');
  await page.evaluate(()=>{window.__stressFrames=[];window.__stressActive=true;let last=0;function tick(t){if(!window.__stressActive)return;if(last)window.__stressFrames.push(t-last);last=t;requestAnimationFrame(tick);}requestAnimationFrame(tick);});
  const samples=[];
  for(let pass=0;pass<6;pass++){
   const before=await page.evaluate(()=>Number(document.getElementById('atlasMap').dataset.gpuFeatureScans||0));
   for(const [lng,lat,zoom] of cameras){
    await page.evaluate(coords=>window.NordlEnergyAtlas.getMap().jumpTo({center:[coords[0],coords[1]],zoom:coords[2],bearing:0,pitch:0}),[lng,lat,zoom]);
    await page.waitForTimeout(110);
   }
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='gpu-vector',null,{timeout:25000});
   const scanned=await page.evaluate(()=>Number(document.getElementById('atlasMap').dataset.gpuFeatureScans||0));
   // A runaway per-render feature scanner would exceed the camera budget.
   assert.ok(scanned-before<=60,'Excessive full-viewport scans in twelve camera moves: '+(scanned-before));
   await page.locator('#globalGpu').uncheck();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='viewport-clusters',null,{timeout:20000});
   await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols)>0,null,{timeout:15000});
   await page.locator('#globalGpu').check();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='gpu-vector'&&Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols)>0,null,{timeout:60000});
   assert.equal(await page.locator('#globalGdw').isChecked(),true,'Independent dam overlay must survive GPU mode changes');
   const heapMiB=await readHeap();
   const counters=await page.evaluate(()=>{const h=document.getElementById('atlasMap');return {records:Number(h.dataset.globalAssetRecords||0),gdwRecords:Number(h.dataset.gdwAssetRecords||0),gpuScans:Number(h.dataset.gpuFeatureScans||0),renderer:h.dataset.globalRenderer,visible:Number(h.dataset.globalVisibleSymbols||0),gdwRenderer:h.dataset.gdwRenderer};});
   assert.ok(counters.records>30000&&counters.gdwRecords===41145&&counters.visible>0,'Approved sources disappeared after stress');
   samples.push({pass:pass+1,heapMiB,fullScansInPass:scanned-before,counters});
  }
  const frameDeltas=await page.evaluate(()=>{window.__stressActive=false;return window.__stressFrames.slice();});
  const actual=frameDeltas.filter(v=>Number.isFinite(v)&&v>=0);
  assert.ok(actual.length>=50,'No measured browser animation frames during stress');
  assert.deepEqual(errors,[],'Page errors or failed dataset requests');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4),'Viewport overflow '+width);
  assert.equal(requests.filter(x=>x==='/data/global-plants-wri-v130.json').length,1,'WRI archive must remain cached during interactions');
  assert.ok(!requests.some(x=>x.startsWith('/data/osm-odbl/')||x.startsWith('/data/osm-grid-odbl/')),'Unselected licensing-separated overlays requested');
  const first=samples[1].heapMiB,last=samples[samples.length-1].heapMiB;
  assert.ok(last<=first+96,'Post-GC V8 heap grew over loose 96 MiB alarm: '+JSON.stringify(samples));
  const result={version:'V90.6g4e',width,mode:'headless Chromium/SwiftShader CI; not physical GPU or VRAM',
   cameraMoves:cameras.length*samples.length,gpuModeCycles:samples.length,sourceRecords:34936,damRecords:41145,
   samples,frameCount:actual.length,rafMs:{median:percentile(actual,.5),p95:percentile(actual,.95),p99:percentile(actual,.99),max:Math.max(...actual)},
   pmtilesRangeResponses:ranges,pmtilesResponseBytes:rangeBytes,requests,sourceResponses:responses,errors};
  fs.writeFileSync(path.join(output,'atlas-stress-'+width+'.json'),JSON.stringify(result,null,2));
  await page.locator('#atlasMap').screenshot({path:path.join(output,'atlas-stress-'+width+'.png')});
  console.log('PASS V90.6g4e sustained atlas stress',JSON.stringify({width,cameraMoves:result.cameraMoves,gpuModeCycles:result.gpuModeCycles,heapMiB:samples.map(s=>s.heapMiB),rafP95Ms:result.rafMs.p95,rangeResponses:ranges,fullScans:samples.map(s=>s.fullScansInPass)}));
  await page.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
