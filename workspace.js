/* Workspace presentation; all published values still come from energy.json. */
(() => {
  'use strict';
  const get=id=>document.getElementById(id);
  const theme=get('enTheme');
  function setTheme(t){document.body.dataset.theme=t;if(theme){theme.textContent=t==='light'?'☀':'☾';theme.setAttribute('aria-pressed',String(t==='light'));}try{localStorage.setItem('energy-theme',t);}catch{}}
  try{const t=localStorage.getItem('energy-theme');setTheme(t==='light'?'light':'dark');}catch{setTheme('dark');}
  theme?.addEventListener('click',()=>setTheme(document.body.dataset.theme==='light'?'dark':'light'));
  const nav=get('enNav'), menu=get('enMenu');
  function closeMenu(){nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false');}
  menu?.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));if(open)nav.querySelector('a')?.focus();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav?.classList.contains('open')){closeMenu();menu?.focus();}});
  document.addEventListener('pointerdown',e=>{if(nav?.classList.contains('open')&&!nav.contains(e.target)&&!menu?.contains(e.target))closeMenu();});
  const links=[...document.querySelectorAll('.en-link[href^="#"]')];
  function active(id){links.forEach(a=>{const on=a.getAttribute('href')==='#'+id;a.classList.toggle('active',on);if(on)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}
  links.forEach(a=>a.addEventListener('click',()=>{active(a.hash.slice(1));closeMenu();}));
  window.addEventListener('hashchange',()=>active(location.hash.slice(1)||'overview'));
  active(location.hash.slice(1)||'overview');
  get('enSearch')?.addEventListener('submit',e=>{e.preventDefault();const q=get('enQuery').value.trim().toLowerCase();if(!q)return;const aliases={electricity:'prices',power:'prices',spot:'prices',price:'prices',map:'energyMap',substation:'grid',transmission:'grid',snow:'weather',rain:'weather',reservoir:'hydro',storage:'hydro',hydrology:'hydroLab',powerplant:'plants','power plant':'plants',company:'plants',ownership:'plants',api:'datasets',csv:'datasets',download:'datasets',history:'history',solar:'calculators',ev:'calculators',oil:'fuels',freight:'fuels'};const hit=links.find(a=>!a.hidden&&a.textContent.toLowerCase().includes(q))||links.find(a=>a.hash==='#'+aliases[q]);get('enSearchStatus').textContent=hit?'Opening '+hit.textContent:'No energy section matched '+q;if(hit){location.hash=hit.hash;active(hit.hash.slice(1));closeMenu();}else get('enQuery').focus();});
  function filterZones(){const q=(get('enZoneSearch')?.value||'').trim().toLowerCase();const rows=[...document.querySelectorAll('#zones .zone')];let n=0;rows.forEach(r=>{r.hidden=!!q&&!r.textContent.toLowerCase().includes(q);if(!r.hidden)n++;});if(get('enZoneCount'))get('enZoneCount').textContent=n+' of '+rows.length+' zones';}
  get('enZoneSearch')?.addEventListener('input',filterZones);
  function element(tag,value){const e=document.createElement(tag);e.textContent=String(value);return e;}
  function kpi(label,value,note){const e=document.createElement('article');e.className='en-kpi';e.append(element('small',label),element('b',value),element('span',note));return e;}
  function render(d){if(!get('enKpis'))return;const rows=[];
    for(const z of d.zones||[]){const v=z.today?.eur;if(window.NordlData.comparable(z)&&Array.isArray(v)&&v.length&&v.every(Number.isFinite))rows.push({code:z.zone,value:v.reduce((a,b)=>a+b,0)/v.length*100});}
    for(const z of d.europe||[]){const v=z.cents;if(window.NordlData.comparable(z)&&Array.isArray(v)&&v.length&&v.every(Number.isFinite)&&!rows.some(r=>r.code===z.zone))rows.push({code:z.zone,value:v.reduce((a,b)=>a+b,0)/v.length});}
    rows.sort((a,b)=>a.value-b.value);
    const low=rows[0], high=rows.at(-1), fmt=v=>v.toFixed(1)+' ¢';
    const reservoir=Object.entries(d.reservoirs?.zones||{}).filter(([,v])=>Number.isFinite(v.vsNormal)).sort((a,b)=>a[1].vsNormal-b[1].vsNormal)[0];
    get('enKpis').replaceChildren(kpi('Power zones',rows.length||'—','With usable price series; stale European rows excluded'),kpi('Lowest average',low?fmt(low.value):'—',low?low.code+' · EUR cents/kWh':'Not available'),kpi('Highest average',high?fmt(high.value):'—',high?high.code+' · EUR cents/kWh':'Not available'),kpi('Hydro vs seasonal median',reservoir?(reservoir[1].vsNormal*100).toFixed(1)+' pp':'—',reservoir?reservoir[0]+' · lowest available deviation':'Not available'));
    const stamp=Date.parse(d.generated), hours=(Date.now()-stamp)/36e5;
    const status=!Number.isFinite(stamp)||hours<-.1?'Unknown snapshot time':hours>3?'Stale snapshot':'Published snapshot';
    get('enTape').textContent=status+' · '+(Number.isFinite(stamp)?new Date(stamp).toLocaleString():'timestamp unavailable')+(rows.length?' · '+rows.length+' usable price zones':'');
    const counts=[['Power price zones',rows.length],['Hydro areas',Object.keys(d.reservoirs?.zones||{}).length],['Weather areas',Object.keys(d.weather||{}).length],['Grid flow links',(d.grid?.flows||[]).length],['Commodity series',(d.commodities||[]).length],['Gas storage countries',(d.gasStorage?.countries||[]).length],['Company margin models',(d.market?.margins||[]).length],['Project news',(d.news||[]).length]];
    const cards=counts.map(([name,n])=>{const e=document.createElement('article');e.append(element('b',name),element('span',n?n+' entries in snapshot':'Not available in snapshot'));return e;});
    get('enHealth').replaceChildren(...cards,element('p','Collection time is not the observation time. Storage is weekly; forecasts have validity dates; market indicators may be delayed.'));filterZones();
  }
  window.addEventListener('energy:snapshot',e=>render(e.detail));
  window.addEventListener('energy:unavailable',()=>{if(get('enKpis'))get('enKpis').replaceChildren(kpi('Data unavailable','—','No current values loaded'));if(get('enHealth'))get('enHealth').textContent='No snapshot available.';if(get('enTape'))get('enTape').textContent='Data unavailable';});
  // Existing inline fetch may complete before this deferred script in a cached load.
  if(typeof DATA!=='undefined'&&DATA)render(DATA);else if(get('stamp')?.classList.contains('stale')&&get('stamp').textContent==='could not load data')window.dispatchEvent(new Event('energy:unavailable'));
})();