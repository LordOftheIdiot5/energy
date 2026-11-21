const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
const source=JSON.parse(fs.readFileSync('data/gem-gas-202511/gem-gas-pipelines-202511-v1.json','utf8'));
const candidate=source.rows.find(r=>r.status==='operating'&&r.start_country&&r.id);
assert.ok(candidate);
const PIPE='/data/gem-gas-202511/';
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
 for(const width of [1440,1024,390]){
  const page=await browser.newPage({viewport:{width,height:940}}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith(PIPE))requests.push(path);});
  await page.goto(base+'#energyMap',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
  assert.equal(requests.length,0,'GEM data must be opt-in at '+width);
  const started=Date.now();
  await page.locator('#globalGemPipelines').check();
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRenderedFeatures==='3921',null,{timeout:65000});
  await page.waitForFunction(()=>{
   const m=window.NordlEnergyAtlas?.getMap(),f=m?.getFilter('nordl-gem-gas-routes');
   return Array.isArray(f)&&f[0]==='=='&&f[2]==='operating';
  },null,{timeout:25000});
  const latency=Date.now()-started;
  assert.equal(requests.filter(x=>x.endsWith('gem-gas-pipelines-202511-v1.json')).length,1);
  assert.equal(requests.filter(x=>x.endsWith('gem-gas-pipeline-routes-202511-v1.geojson')).length,1);
  const first=await page.evaluate(()=>{
    const m=window.NordlEnergyAtlas.getMap(),f=m.getFilter('nordl-gem-gas-routes');
    window.__gemFilterCalls=[];
    const original=m.setFilter.bind(m);
    m.setFilter=function(id,filter,...args){
     if(id==='nordl-gem-gas-routes')window.__gemFilterCalls.push({size:JSON.stringify(filter).length,filter,at:performance.now()});
     return original(id,filter,...args);
    };
    return {filter:f,source:m.getSource('nordl-gem-gas-lines')!=null,layer:m.getLayer('nordl-gem-gas-routes')!=null};
  });
  assert.ok(first.source&&first.layer);
  assert.ok(JSON.stringify(first.filter).length<90,'Starting source status filter must remain compact');
  await page.locator('#gemStatus').selectOption('construction');
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRecords==='282');
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getFilter('nordl-gem-gas-routes')?.[2]==='construction');
  await page.locator('#gemStatus').selectOption('proposed');
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRecords==='611');
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getFilter('nordl-gem-gas-routes')?.[2]==='proposed');
  await page.locator('#gemStatus').selectOption('');
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRecords==='4246');
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getFilter('nordl-gem-gas-routes')==null);
  const controls=page.locator('#globalGemPipelines').locator('xpath=ancestor::div[contains(@class,"atlas-digital-controls")]');
  await controls.locator('details').evaluate(e=>e.open=true);
  await page.locator('#gemCountry').selectOption(candidate.start_country);
  await page.waitForFunction(country=>{
   const f=window.NordlEnergyAtlas.getMap().getFilter('nordl-gem-gas-routes');
   return Array.isArray(f)&&f[0]==='any'&&JSON.stringify(f).includes(country);
  },candidate.start_country);
  const beforeSearch=await page.evaluate(()=>window.__gemFilterCalls.length);
  const id=candidate.id;
  for(const n of [1,2,Math.min(5,id.length),id.length])await page.locator('#gemSearch').fill(id.slice(0,n));
  await page.waitForFunction(id=>[...document.querySelector('#gemResults').options].some(o=>o.value===id),id,{timeout:15000});
  await page.waitForTimeout(230);
  const after=await page.evaluate(()=>({
    calls:window.__gemFilterCalls,filter:window.NordlEnergyAtlas.getMap().getFilter('nordl-gem-gas-routes')
  }));
  assert.ok(after.calls.length-beforeSearch<=1,'Burst text edits should trigger at most one expensive map filter update');
  assert.ok(JSON.stringify(after.filter).includes(id),'Map text filter must retain exact native pipeline ID');
  assert.ok(after.calls.every(x=>x.size<15000),'No large full-source ID filters for common controls');
  await page.locator('#gemResults').selectOption(id);
  const inspector=await page.locator('#gemPipelineInspector').innerText();
  assert.ok(inspector.includes('November 2025')&&inspector.includes('CC BY 4.0')&&inspector.includes(candidate.name));
  await page.locator('#gemSearch').fill('');
  await page.locator('#gemCountry').selectOption('');
  await page.locator('#gemStatus').selectOption('operating');
  await page.waitForFunction(()=>document.querySelector('#atlasMap').dataset.gemRecords==='2975');
  // Camera movements and mixed source overlays must preserve the 3,921 source geometries.
  const camStart=Date.now();
  await page.evaluate(()=>{
   const m=window.NordlEnergyAtlas.getMap();m.jumpTo({center:[0,25],zoom:1,bearing:0,pitch:0});
  });
  await page.waitForTimeout(300);
  await page.evaluate(()=>{
   const m=window.NordlEnergyAtlas.getMap();m.jumpTo({center:[10,50],zoom:4,bearing:0,pitch:0});
  });
  await page.waitForTimeout(300);
  const cameraMs=Date.now()-camStart;
  assert.equal(await page.locator('#atlasMap').getAttribute('data-gem-rendered-features'),'3921');
  await page.locator('#globalNaceiHistoric').check();
  await page.waitForFunction(()=>Number(document.querySelector('#atlasMap').dataset.naceiRecords)>0,null,{timeout:65000});
  await page.locator('#globalGemPipelines').uncheck();
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getLayoutProperty('nordl-gem-gas-routes','visibility')==='none');
  assert.ok(await page.locator('#globalNaceiHistoric').isChecked(),'GEM must not disable unrelated NACEI overlay');
  await page.locator('#globalGemPipelines').check();
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getLayoutProperty('nordl-gem-gas-routes','visibility')==='visible');
  assert.equal(requests.filter(x=>x.endsWith('gem-gas-pipelines-202511-v1.json')).length,1,'Retoggle should reuse session catalog');
  assert.equal(requests.filter(x=>x.endsWith('gem-gas-pipeline-routes-202511-v1.geojson')).length,1,'Retoggle should reuse session routes');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4),'No horizontal overflow '+width);
  assert.deepEqual(errors,[],'No JS errors '+width);
  console.log('PASS V90.6g4 GEM performance '+width+'px',JSON.stringify({
   initialDataReadyMs:latency,filteredCalls:after.calls.length,filterCallsDuringBurst:after.calls.length-beforeSearch,
   maxFilterBytes:Math.max(0,...after.calls.map(x=>x.size)),cameraTwoJumpsMs:cameraMs,
   sourceRequests:requests.filter(x=>x.startsWith(PIPE)).length,sourceRoutes:3921,nativeRecords:4246
  }));
  await page.close();
 }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
