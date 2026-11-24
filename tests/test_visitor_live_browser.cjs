/* V91-P0 live homepage acceptance: real deployed production, not fixtures. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base='https://energy.nordl.dev/';
fs.mkdirSync('visitor-live',{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const width of [1440,390]){
   const page=await browser.newPage({viewport:{width,height:900}});
   const errors=[],http=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('response',r=>{if(new URL(r.url()).origin===new URL(base).origin&&/\/(data\/energy\.json|data\/fingrid-v1\.json)(\?|$)/.test(new URL(r.url()).pathname+new URL(r.url()).search)&&!r.ok())http.push({url:r.url(),status:r.status()});});
   await page.goto(base,{waitUntil:'domcontentloaded',timeout:60000});
   await page.waitForFunction(()=>document.querySelector('#enKpis .en-kpi')?.textContent?.includes('NO3 day-ahead average'),null,{timeout:30000});
   await page.waitForFunction(()=>document.querySelector('#visualStamp')?.textContent?.startsWith('Snapshot'),null,{timeout:30000});
   await page.waitForFunction(()=>!document.querySelector('#monitorFingrid')?.textContent?.includes('Loading published measurements'),null,{timeout:30000});
   const result=await page.evaluate(()=>({
    no3:document.querySelector('#enKpis .en-kpi')?.innerText,
    hydro:document.querySelector('#visualHydro')?.innerText,
    price:document.querySelector('#visualPrice')?.innerText,
    fingrid:document.querySelector('#monitorFingrid')?.innerText,
    stamp:document.querySelector('#visualStamp')?.innerText,
    bodyWidth:document.documentElement.scrollWidth,viewport:innerWidth,
    energy:typeof DATA!=='undefined'&&DATA?{generated:DATA.generated,no3:DATA.zones.find(z=>z.zone==='NO3')?.today?.date,nve:DATA.reservoirs?.week}:null
   }));
   assert.ok(result.energy?.generated,'No parsed public energy snapshot');
   assert.match(result.no3,/NO3 day-ahead average/);
   assert.ok(result.no3.includes(result.energy.no3)||result.no3.includes('No complete NO3 delivery'),'Delivery provenance or gap must be visible');
   for(const [k,v] of Object.entries({hydro:result.hydro,price:result.price,fingrid:result.fingrid}))
     assert.doesNotMatch(v||'',/^(Awaiting reservoir data|Awaiting published data|Loading published measurements)/i,'Unresolved '+k);
   assert.ok(result.bodyWidth<=result.viewport+12,'Horizontal overflow at '+width);
   assert.deepEqual(errors,[],'Page JavaScript errors');
   assert.deepEqual(http,[],'Snapshot or measurements HTTP errors');
   await page.screenshot({path:'visitor-live/home-'+width+'.png'});
   await page.evaluate(()=>location.hash='energyMap');
   await page.waitForFunction(()=>document.getElementById('energyMap')?.getBoundingClientRect().width>0,null,{timeout:30000});
   await page.evaluate(()=>location.hash='datasets');
   await page.waitForFunction(()=>document.getElementById('datasets')?.getBoundingClientRect().width>0,null,{timeout:30000});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+12));
   console.log('V91 live',width,JSON.stringify({generated:result.energy.generated,no3Date:result.energy.no3,nveWeek:result.energy.nve,stamp:result.stamp,fingrid:result.fingrid?.slice(0,160)}));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
