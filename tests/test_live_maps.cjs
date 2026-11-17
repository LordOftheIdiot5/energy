const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const base='https://energy.nordl.dev/';
const out='map-verification';
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1050},deviceScaleFactor:1});
 const tiles=new Set(),errors=[];
 page.on('response',r=>{if(r.ok()&&(/\.(pbf|mvt)(\?|$)/i.test(r.url())||/protobuf|mapbox-vector-tile/i.test(r.headers()['content-type']||''))&&new URL(r.url()).hostname.endsWith('openfreemap.org'))tiles.add(r.url());});
 page.on('pageerror',e=>{errors.push(e.message);console.log('PAGE ERROR:',e.message);});
 const ready=async(selector,min=1)=>{await page.waitForFunction(({selector,min})=>[...document.querySelectorAll(selector)].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';}).length>=min,{selector,min},{timeout:60000});};
 const shot=async(name,selector)=>{await page.locator(selector).screenshot({path:out+'/'+name+'.png',timeout:30000});};
 const report=(name,data)=>console.log(name,JSON.stringify(data));
 try{
  await page.goto(base+'#plants',{waitUntil:'domcontentloaded',timeout:60000});
  await page.locator('#geoLayer').selectOption('europe');
  await page.waitForFunction(()=>Number(document.querySelector('#geoEuropeMap')?.dataset.recordCount)>10000,{}, {timeout:60000});
  await ready('#geoEuropeMap button[data-asset-count]',5);
  await page.waitForFunction(()=>document.querySelector('#geoEuropeMap .maplibregl-canvas')?.getBoundingClientRect().width>0,{}, {timeout:30000});
  for(let i=0;i<30&&!tiles.size;i++)await page.waitForTimeout(1000);
  assert.ok(tiles.size>0,'No successful real OpenFreeMap vector tiles');
  report('EUROPE',{records:await page.locator('#geoEuropeMap').getAttribute('data-record-count'),markers:await page.locator('#geoEuropeMap button[data-asset-count]').count(),realVectorTiles:tiles.size});
  await shot('01-europe-plants','#geoEuropeMap');
  await page.locator('#geoFuel').selectOption('Hydro');
  await page.waitForFunction(()=>{const n=Number(document.querySelector('#geoEuropeMap').dataset.recordCount);return n>0&&n<10000;});
  await ready('#geoEuropeMap button[data-asset-count]');
  await page.locator('#geoLayer').selectOption('stations');
  await page.waitForFunction(()=>document.getElementById('geoTerrain').value==='context'&&Number(document.querySelector('#geoEuropeMap').dataset.recordCount)>1000);
  await ready('#geoEuropeMap button[data-asset-count]',5);
  await shot('02-norway-stations','#geoEuropeMap');
  await page.locator('#geoLayer').selectOption('catchments');
  await page.waitForFunction(()=>Number(document.querySelector('#geoEuropeMap').dataset.recordCount)>1000&&Number(document.querySelector('#geoEuropeMap').dataset.renderedPolygons)>0,{}, {timeout:60000});
  await shot('03-norway-catchments','#geoEuropeMap');
  report('NORWAY',{catchments:await page.locator('#geoEuropeMap').getAttribute('data-record-count'),polygonFragments:await page.locator('#geoEuropeMap').getAttribute('data-rendered-polygons')});
  await page.goto(base+'#hydro',{waitUntil:'domcontentloaded',timeout:60000});
  await ready('#atlasMap [data-observation]',5);
  await shot('04-hydro','#atlasMap');
  await page.locator('#energyMap [data-layer="weather"]').click();
  await page.waitForFunction(()=>window.NordlEnergyMapSnapshot?.layer==='weather'&&document.querySelectorAll('#atlasMap [data-observation]').length===window.NordlEnergyMapSnapshot.rows.length,{}, {timeout:60000});
  await ready('#atlasMap [data-observation]');
  await shot('05-weather','#atlasMap');
  await page.goto(base+'#news',{waitUntil:'domcontentloaded',timeout:60000});
  const projects=await page.request.get(base+'data/energy-projects-v1.json');assert.ok(projects.ok());const projectData=await projects.json();
  if(projectData.rows.length){await ready('#projectAtlas [data-project-id]',6);}else{assert.match(projectData.coverage,/pending commercial review/i);assert.ok(await page.locator('.en-project-sources a').first().isVisible());assert.equal(await page.locator('#projectAtlas [data-project-id]').count(),0);}
  await shot('06-projects','#projectAtlas');
  await page.goto(base+'#gas',{waitUntil:'domcontentloaded',timeout:60000});
  await ready('#gasAtlas [data-gas-code]');
  await shot('07-gas','#gasAtlas');
  const snapshot=await (await page.request.get(base+'data/energy.json')).json();assert.equal(snapshot.publication.policy,'v90.1_open_projection');assert.equal(snapshot.commodities.length,0);assert.deepEqual(snapshot.zones.map(x=>x.zone).sort(),['NO1','NO2','NO3','NO4','NO5','SE1','SE2','SE3','SE4']);assert.equal(snapshot.marketIndex,null);assert.deepEqual(snapshot.market,{});const wri=await (await page.request.get(base+'data/europe-plants-v1.json')).json();assert.equal((await page.request.get(base+'plants/wri/'+wri.rows[0].id+'/')).status(),200);assert.equal((await page.request.get(base+'data-coverage/')).status(),200);assert.equal((await page.request.get(base+'scripts/fetch.py')).status(),404);
  report('LIVE MAP VERIFICATION',{realVectorTiles:tiles.size,pageErrors:errors});
  assert.equal(errors.length,0,'Unexpected page JavaScript errors');
 }catch(error){await page.screenshot({path:out+'/failure.png',fullPage:false}).catch(()=>{});throw error;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});