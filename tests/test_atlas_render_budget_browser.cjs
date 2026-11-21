const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const BASE=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
const PUB=process.env.ATLAS_PUBLIC_DIR;
if(!PUB)throw Error('ATLAS_PUBLIC_DIR required for exact staged PMTiles source');
const manifest=JSON.parse(fs.readFileSync(path.join(PUB,'data/atlas-tiles/index-v1.json'),'utf8'));
const archive=fs.readFileSync(path.join(PUB,'data/atlas-tiles',manifest.path));
const optional=/^\/data\/(?:global-plants-wri-v130\.json|gdw\/|osm-grid-odbl\/|osm-odbl\/|atlas-tiles\/)/;
const measure=async page=>page.evaluate(()=>({landPaints:Number(document.getElementById('atlasMap').dataset.worldLandPaints||0),
 filterPasses:Number(document.getElementById('atlasMap').dataset.globalFilterPasses||0),
 gpuScans:Number(document.getElementById('atlasMap').dataset.gpuFeatureScans||0),
 gpuScanMs:Number(document.getElementById('atlasMap').dataset.gpuFeatureScanMs||0),
 renderer:document.getElementById('atlasMap').dataset.globalRenderer,
 records:Number(document.getElementById('atlasMap').dataset.globalAssetRecords||0),
 visible:Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols||0),
 world:document.getElementById('atlasMap').dataset.worldBasemap}));
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const width of [1440,1024,390]){
   const page=await browser.newPage({viewport:{width,height:930}}),requests=[],errors=[];
   let tileRanges=0,tileBytes=0,renderFrames=0;
   page.on('pageerror',e=>errors.push(String(e)));
   page.on('request',r=>{const p=new URL(r.url()).pathname;if(optional.test(p))requests.push(p);});
   await page.route('**/pmtiles@4.5.0/dist/pmtiles.js',route=>route.fulfill({path:require.resolve('pmtiles').replace(/dist.*$/,'dist/pmtiles.js'),contentType:'text/javascript'}));
   await page.route('**/data/atlas-tiles/*.pmtiles',async route=>{
    const m=/^bytes=(\d+)-(\d+)$/.exec(route.request().headers().range||'');
    if(!m){await route.fulfill({status:400,body:'Range required'});return;}
    const start=Number(m[1]),end=Math.min(Number(m[2]),archive.length-1);
    tileRanges++;tileBytes+=end-start+1;
    await route.fulfill({status:206,headers:{'Content-Range':'bytes '+start+'-'+end+'/'+archive.length,
     'Content-Length':String(end-start+1),'Accept-Ranges':'bytes','ETag':'"atlas-perf"',
     'Content-Type':'application/octet-stream'},body:archive.subarray(start,end+1)});
   });
   await page.goto(BASE,{waitUntil:'domcontentloaded'});
   await page.waitForTimeout(300);
   assert.equal(requests.length,0,'Homepage must not preload optional Atlas archives');
   await page.goto(BASE+'#energyMap',{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
   await page.waitForTimeout(250);
   assert.equal(requests.length,0,'Disabled Atlas layers must not fetch optional sources');
   await page.locator('#globalWri').check();
   await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols)>0&&Number(document.getElementById('atlasMap').dataset.globalAssetRecords)>30000,null,{timeout:65000});
   const one=await measure(page);
   assert.ok(one.filterPasses>=1,'Filter instrumentation was not used');
   assert.equal(requests.filter(p=>p==='/data/global-plants-wri-v130.json').length,1);
   assert.ok(!requests.some(p=>/\/gdw\/|\/osm-odbl\/|\/osm-grid-odbl\//.test(p)),'Unselected rights-scoped sources loaded');
   await page.locator('#atlasWorld').click();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.worldBasemap==='natural-earth-5.1.2',null,{timeout:20000});
   const svg1=await page.locator('#atlasMap .atlas-local-world path').getAttribute('d');
   assert.ok(svg1.length>10000,'Actual Natural Earth path missing');
   const base=await measure(page);
   // Many move callbacks without a changed camera must NOT reproject the
   // whole Natural Earth source. The final settled camera still must paint.
   await page.evaluate(()=>{const m=window.NordlEnergyAtlas.getMap();for(let i=0;i<60;i++)m.fire('move');});
   await page.waitForTimeout(350);
   const same=await measure(page);
   assert.ok(same.landPaints<=base.landPaints+1,'Redundant static SVG reprojection '+JSON.stringify({base,same}));
   assert.equal(same.filterPasses,base.filterPasses,'Camera events must not refilter 30k WRI rows');
   await page.evaluate(()=>window.NordlEnergyAtlas.getMap().jumpTo({center:[25,5],zoom:2,bearing:0,pitch:0}));
   await page.waitForFunction(n=>Number(document.getElementById('atlasMap').dataset.worldLandPaints)>n,base.landPaints,{timeout:16000});
   const svg2=await page.locator('#atlasMap .atlas-local-world path').getAttribute('d');
   assert.notEqual(svg1,svg2,'Final camera must reproject Natural Earth correctly');
   const moved=await measure(page);
   assert.equal(moved.filterPasses,base.filterPasses);
   await page.locator('#globalFind').evaluate(e=>e.closest('details').open=true);
   await page.locator('#globalFind').fill('Follafoss');
   await page.waitForFunction(()=>[...document.getElementById('globalResults').options].some(x=>x.textContent.includes('Follafoss')),null,{timeout:15000});
   const searched=await measure(page);
   assert.ok(searched.filterPasses>base.filterPasses,'New source filter must re-evaluate');
   await page.locator('#globalFind').fill('');
   await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.globalAssetRecords)>30000);
   await page.locator('#globalGpu').check();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='gpu-vector',null,{timeout:65000});
   assert.ok(tileRanges>0,'PMTiles signed source had no range requests');
   await page.waitForTimeout(250);
   const pre=await measure(page);
   assert.ok(pre.gpuScans>0&&pre.visible>0);
   const cdp=await page.context().newCDPSession(page);
   const heapBefore=await cdp.send('Runtime.getHeapUsage');
   // A painted GPU layer must not enumerate all rendered features per frame.
   const frames=await page.evaluate(async()=>{
    const m=window.NordlEnergyAtlas.getMap();let renders=0;
    const count=()=>{renders++;};m.on('render',count);
    try{for(let i=0;i<30;i++){await new Promise(resolve=>requestAnimationFrame(resolve));m.triggerRepaint();}
     await new Promise(resolve=>setTimeout(resolve,250));return renders;}
    finally{m.off('render',count);}
   });
   renderFrames=frames;
   const after=await measure(page);
   assert.ok(frames>=10,'Must observe actual rendered frames, not only static timers');
   assert.ok(after.gpuScans-pre.gpuScans<=Math.ceil(frames/3)+2,
    'Excessive GPU-wide feature enumeration on render: '+JSON.stringify({pre,after,frames}));
   await page.evaluate(()=>window.NordlEnergyAtlas.getMap().jumpTo({center:[-80,25],zoom:2,bearing:0,pitch:0}));
   await page.waitForFunction(n=>Number(document.getElementById('atlasMap').dataset.gpuFeatureScans)>n,after.gpuScans,{timeout:30000});
   const postMove=await measure(page);
   const heapAfter=await cdp.send('Runtime.getHeapUsage');
   await page.locator('#globalGpu').uncheck();
   await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.globalRenderer==='viewport-clusters');
   assert.ok(Number(await page.locator('#atlasMap').getAttribute('data-global-visible-symbols'))>0,'Fallback GPU-off symbols missing');
   await page.locator('#globalWri').uncheck();
   await page.locator('#globalWri').check();
   await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.globalVisibleSymbols)>0);
   assert.equal(requests.filter(p=>p==='/data/global-plants-wri-v130.json').length,1,'Toggling must reuse original source archive');
   assert.deepEqual(errors,[],'Unexpected browser page error '+width);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4),'Horizontal mobile overflow '+width);
   console.log('PASS V90.6g4d actual map resource budget',JSON.stringify({
     width,initial:one,svgBase:base,svgAfterNoCameraChange:same,svgAfterCamera:moved,
     gpuBefore:pre,gpuAfterThirtyFrames:after,gpuAfterCamera:postMove,
     observedFrames:frames,gpuExtraFullScans:after.gpuScans-pre.gpuScans,
     heapBeforeMiB:Math.round(heapBefore.usedSize/1048576*10)/10,
     heapAfterMiB:Math.round(heapAfter.usedSize/1048576*10)/10,
     archiveRequests:requests.length,tileRanges,tileBytes,
     fallback:true,failures:errors.length
   }));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
