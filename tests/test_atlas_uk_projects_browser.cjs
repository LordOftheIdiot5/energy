const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const base=process.env.ENERGY_TEST_URL||'http://127.0.0.1:8766/';
 try{const source=JSON.parse(fs.readFileSync('data/uk-repd-projects-v1.json','utf8'));const known=source.rows.find(r=>r.status==='Decommissioned'&&r.country==='Wales');
 assert.ok(known,'Official UK fixture record missing');
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'#energyMap',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed(),null,{timeout:60000});
  const staged=await page.request.get(base+'data/uk-repd-projects-v1.json');
  assert.equal(staged.status(),200);const doc=await staged.json();assert.equal(doc.rows.length,14388);
  await page.locator('#globalUkProjects').check();
  await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.ukRecords==='14388',null,{timeout:60000});
  await page.locator('#ukProjectView').click();
  await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.ukMarkers)>0,null,{timeout:30000});
  const visible=await page.locator('#atlasMap .atlas-uk-project-marker').count();
  assert.ok(visible>0&&visible<1100, 'UK viewport markers must be bounded: '+visible);
  await page.locator('#atlasFitSource').selectOption('uk');
  await page.locator('#atlasFitActive').click();
  await page.waitForFunction(()=>window.NordlEnergyAtlas.getMap().getCenter().lng<6,null,{timeout:30000});
  const detail=page.locator('#globalUkProjects').locator('xpath=ancestor::div[contains(@class,"atlas-digital-controls")]');
  await detail.locator('details').evaluate(e=>e.open=true);
  await page.locator('#ukProjectCountry').selectOption(known.country);
  await page.locator('#ukProjectStage').selectOption(known.status);
  await page.locator('#ukProjectFind').fill(known.id);
  await page.waitForFunction(id=>[...document.getElementById('ukProjectResults').options].some(o=>o.value===id),known.id,{timeout:20000});
  await page.locator('#ukProjectResults').selectOption(known.id);
  const inspection=await page.locator('#ukProjectInspector').innerText();
  assert.ok(inspection.includes(known.name));
  assert.ok(inspection.includes(known.status));
  assert.ok(inspection.includes('source-reported'));
  assert.ok(await page.locator('#ukProjectInspector a[href*="gov.uk"]').isVisible());
  await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.ukMarkers)>0,null,{timeout:15000});
  const target=await page.locator('#atlasMap .atlas-uk-project-marker').count();assert.ok(target>0);
  await page.locator('#globalProjects').check();
  await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.projectRecords)>1000,null,{timeout:60000});
  await page.locator('#globalUkProjects').uncheck();
  await page.waitForFunction(()=>document.getElementById('atlasMap').dataset.ukMarkers==='0');
  assert.ok(await page.locator('#globalProjects').isChecked(),'UK toggle should not affect Norwegian NVE licenses');
  assert.deepEqual(errors,[],'No uncaught errors while navigating UK data on '+width);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4),'Responsive width '+width);
  console.log('PASS UK projects desktop/mobile '+width+' · 14388 data records · '+visible+' visible clusters');
  await page.close();
 }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
