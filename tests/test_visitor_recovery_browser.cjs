/* V91-P0: real Chromium checks for failed, recovered and retained snapshots. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base='http://127.0.0.1:8765/';
const routePattern='**/data/energy.json?cb=*';

(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try{
    for(const width of [1440,390]){
      const page=await browser.newPage({viewport:{width,height:900}});
      const errors=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.route(routePattern,route=>route.fulfill({status:503,contentType:'text/plain',body:'Simulated snapshot outage'}));
      await page.goto(base,{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>document.querySelector('#staleBar')?.dataset.state==='unavailable');
      await page.waitForFunction(()=>document.querySelector('#visualPrice')?.textContent?.includes('No complete published delivery series'));
      await page.waitForFunction(()=>document.querySelector('#enKpis')?.textContent?.includes('Data unavailable'));
      assert.doesNotMatch(await page.locator('#enKpis').innerText(),/Loading published energy data/i);
      assert.match(await page.locator('#staleBar').innerText(),/No current values can be verified/i);
      assert.equal(await page.locator('#staleBar button').innerText(),'Retry snapshot');
      assert.match(await page.locator('#visualStamp').innerText(),/Data unavailable/i);
      assert.match(await page.locator('#monitorWindows').innerText(),/No complete source price series/i);
      assert.equal(await page.locator('#staleBar a').getAttribute('href'),'https://www.nordpoolgroup.com/');
      await page.unroute(routePattern);
      await page.locator('#staleBar button').click();
      await page.waitForFunction(()=>typeof DATA!=='undefined'&&DATA?.generated&&document.querySelectorAll('#enKpis .en-kpi').length>=4,{timeout:30000});
      await page.waitForFunction(()=>document.querySelector('#visualStamp')?.textContent?.startsWith('Snapshot'),{timeout:30000});
      assert.doesNotMatch(await page.locator('#visualPrice').innerText(),/Awaiting published data/i);
      assert.doesNotMatch(await page.locator('#visualHydro').innerText(),/Awaiting reservoir data/i);
      assert.doesNotMatch(await page.locator('#enKpis').innerText(),/Loading published energy data/i);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+12),'Horizontal overflow at '+width);
      assert.deepEqual(errors,[]);
      await page.screenshot({path:'visitor-recovery-'+width+'.png'});
      if(width===1440){
        const before=await page.locator('#enKpis').innerText();
        // Leave the request pending: the page must abort it after 12 seconds.
        await page.route(routePattern,()=>{});
        await page.evaluate(()=>refreshPublished());
        await page.waitForFunction(
          ()=>document.querySelector('#staleBar')?.textContent?.includes('Refresh failed or timed out'),
          null,{timeout:20000}
        );
        assert.equal(await page.locator('#enKpis').innerText(),before,'Stalled refresh must retain validated data');
        assert.equal(await page.locator('#staleBar button').innerText(),'Retry snapshot');
        await page.unroute(routePattern);
      }
      console.log('V91-P0',width,'initial outage, retry, stalled refresh and layout passed');
      await page.close();
    }
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
