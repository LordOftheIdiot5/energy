(()=>{'use strict';const $=id=>document.getElementById(id);function note(panel,msg,stale){const p=$(panel);if(!p)return;let n=p.querySelector(':scope > .feed-provenance');if(!n){n=document.createElement('p');n.className='feed-provenance';p.insertBefore(n,p.querySelector('h2')?.nextSibling||p.firstChild);}n.textContent=msg;n.dataset.state=stale?'retained':'reported';}
const time=v=>v&&Number.isFinite(Date.parse(v))?new Date(v).toLocaleString():'not supplied';
function render(d){const r=d.reservoirs||{},g=d.grid||{},w=Object.values(d.weather||{}),c=d.commodities||[],gas=d.gasStorage?.countries||[],zones=d.zones||[],e=d.europe||[],price=[...zones,...e],current=new Set(price.filter(window.NordlData.comparable).map(x=>x.zone)),total=new Set(price.map(x=>x.zone));
note('prices','Delivery timezone: Europe/Oslo/CET-CEST · '+current.size+' of '+total.size+' zones verified for today · last-known rows shown separately below current rows',current.size<total.size);
note('day','Hourly aggregation of reported settlement intervals · actual delivery dates and repeated DST hour labels shown; not retail tariffs.',zones.some(z=>!window.NordlData.comparable(z)));
note('grid','Statnett · generation retrieved '+time(g.mixRetrievedAt||g.retrievedAt)+(g.mixStale?' (last known)':'')+' · flows retrieved '+time(g.flowsRetrievedAt||g.retrievedAt)+(g.flowsStale?' (last known)':'')+' · observation times may differ.',!!(g.mixStale||g.flowsStale));
note('weather','MET Norway model forecasts, not station observations · point validity shown per row · '+w.filter(x=>x.stale).length+' retained points',w.some(x=>x.stale));
note('hydro','NVE weekly observation: '+(r.year||'unknown')+' W'+(r.week||'–')+(r.stale?' · last known':'')+' · compare with earlier-year seasonal median.',!!r.stale);
note('gas','GIE aggregate gas day: '+([...new Set(gas.map(x=>x.date).filter(Boolean))].join(', ')||'not supplied')+' · '+gas.filter(x=>x.stale).length+' retained rows',gas.some(x=>x.stale));
note('fuels','Yahoo Finance historical series · source bar dates shown per instrument · '+c.filter(x=>x.stale).length+' retained rows · redistribution review pending; some instruments are ETF proxies.',c.some(x=>x.stale));
note('market','Illustrative margin and historical correlation models, not company forecasts or verified current trading quotes · source dates can differ.',false);
}
window.addEventListener('energy:snapshot',e=>render(e.detail));if(typeof DATA!=='undefined'&&DATA)render(DATA);
})();