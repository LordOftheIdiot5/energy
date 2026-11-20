const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8766/#energyMap');
  await page.waitForFunction(()=>window.NordlEnergyAtlas?.isDetailed()&&!document.getElementById('atlasWorld').disabled,null,{timeout:60000});
  assert.match(await page.locator('#atlasViewStatus').textContent(),/Zoom/);
  assert.equal(await page.locator('#atlasFitActive').isDisabled(),false);
  await page.locator('#globalProjects').check();
  await page.waitForFunction(()=>Number(document.getElementById('atlasMap').dataset.projectRecords)>=1000,null,{timeout:60000});
  await page.locator('#atlasFitSource').selectOption('projects');
  await page.locator('#atlasFitActive').click();
  await page.waitForFunction(()=>{const m=window.NordlEnergyAtlas.getMap(),c=m.getCenter();return m.getZoom()>2&&c.lat>57&&c.lat<72&&c.lng>3&&c.lng<33;},null,{timeout:30000});
  assert.match(await page.locator('#atlasViewStatus').textContent(),/projects/);
  await page.evaluate(()=>window.NordlEnergyAtlas.getMap().jumpTo({bearing:31,pitch:25}));
  await page.locator('#atlasNorth').click();
  assert.ok(await page.evaluate(()=>Math.abs(window.NordlEnergyAtlas.getMap().getBearing())<.01&&Math.abs(window.NordlEnergyAtlas.getMap().getPitch())<.01));
  await page.locator('#atlasVector').click();
  assert.equal(await page.locator('#atlasFitActive').isDisabled(),true);
  await page.locator('#atlasDetailed').click();
  await page.waitForFunction(()=>window.NordlEnergyAtlas.isDetailed()&&!document.getElementById('atlasFitActive').disabled,null,{timeout:30000});
  assert.match(await page.locator('#atlasViewStatus').textContent(),/Zoom/);
  assert.deepEqual(errors,[]);
  console.log('PASS viewport tools',width);
  await page.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
