/* EIA-860M September 2026: preliminary unit inventory, separately from project plans. */
(()=>{'use strict';
const SOURCE='https://www.eia.gov/electricity/data/eia860m/',RIGHTS='https://www.eia.gov/about/copyrights_reuse.php',SHA='bcef74e1af991680731aeecfda967f5950db4ce739bb584edd8b8774c7e6da17';
const PARTS={planned:2357,operating:28712,retired:7303,canceled_postponed:1676};
const COLORS={planned:'#d39631',operating:'#27aa8c',retired:'#8d95a1',canceled_postponed:'#da6980'};
function validateIndex(d){if(d?.schema_version!==1||d.release!=='2026-09'||d.published!=='2026-10-23'||d.source!==SOURCE||d.rights!==RIGHTS||d.source_sha256!==SHA||d.counts?.mapped_rows!==40048||d.counts?.source_rows!==40163||!Array.isArray(d.inventories)||d.inventories.length!==4)throw Error('Unapproved EIA manifest');
const ids=new Set();for(const e of d.inventories){if(!Object.hasOwn(PARTS,e.id)||e.records!==PARTS[e.id]||e.path!=='data/eia860m/'+e.id+'-v1.json'||typeof e.sha256!=='string'||!/^[0-9a-f]{64}$/.test(e.sha256)||ids.has(e.id))throw Error('Unapproved EIA inventory partition');ids.add(e.id);}return d;}
function validatePart(d,kind){if(d?.schema_version!==1||d.release!=='2026-09'||d.inventory!==kind||d.source_sha256!==SHA||d.source!==SOURCE||d.rights!==RIGHTS||!Array.isArray(d.rows)||d.rows.length!==PARTS[kind])throw Error('Unapproved EIA generator data');const seen=new Set();
for(const r of d.rows){const p=r.coordinates;if(r.inventory!==kind||typeof r.id!=='string'||!r.id.startsWith('eia860m-')||seen.has(r.id)||!r.plant||!r.generator_id||!r.status||!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite)||Math.abs(p[0])>180||Math.abs(p[1])>90||'generation_mw' in r||'is_operational' in r)throw Error('Unsafe EIA generator unit');seen.add(r.id);}return d;}
// Select the shortest circular longitude interval, preserving eastern-hemisphere
// territory coordinates and assets either side of the international dateline.
// Bounds may intentionally use an unwrapped east longitude above 180 degrees;
// MapLibre fitBounds accepts this and avoids a nearly-worldwide wrong-way fit.
function sourceBounds(records){
 const points=records.map(r=>r.coordinates).filter(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=180&&Math.abs(p[1])<=90);
 if(!points.length)return null;
 const longs=points.map(p=>(p[0]+360)%360).sort((a,b)=>a-b);
 let gap=-1,after=-1;
 for(let i=0;i<longs.length;i++){
  const span=(i===longs.length-1?longs[0]+360:longs[i+1])-longs[i];
  if(span>gap){gap=span;after=i;}
 }
 let west=longs[(after+1)%longs.length];
 let east=longs[after]+(after===longs.length-1?0:360);
 if(west>=180){west-=360;east-=360;}
 let south=Infinity,north=-Infinity;
 for(const p of points){south=Math.min(south,p[1]);north=Math.max(north,p[1]);}
 return [[west,south],[east,north]];
}
function filtered(records,{state='',technology='',status='',search=''}={}){const q=String(search).trim().toLowerCase();return records.filter(r=>(!state||r.state===state)&&(!technology||r.technology===technology)&&(!status||r.status===status)&&(!q||[r.plant,r.id,r.plant_id,r.generator_id,r.county,r.entity].some(v=>String(v||'').toLowerCase().includes(q))));}
if(typeof module!=='undefined'&&module.exports){module.exports={validateIndex,validatePart,filtered,sourceBounds,PARTS};return;}
const $=id=>document.getElementById(id),host=$('atlasMap'),toggle=$('globalUsGenerators');if(!host||!toggle)return;
const E=(tag,v)=>{const el=document.createElement(tag);if(v!==undefined)el.textContent=String(v);return el;};
let map=null,active=false,manifest=null,indexPromise=null,doc=null,rows=[],pending=new Map(),cache=new Map(),seq=0,frame=0,markers=[],selected='',popup=null,failed=false;
const MAX_CACHED_INVENTORIES=2;
const number=n=>Number(n).toLocaleString('en-US');
function clear(){for(const x of markers)x.remove();markers=[];host.dataset.usMarkers='0';host.dataset.usViewportRecords='0';}
function close(){popup?.remove();popup=null;}
function status(t){$('usGeneratorStatus').textContent=t;}
function bounds(){return sourceBounds(rows);}
function viewUS(){if(!active||!map){status('Open detailed map to explore US generator units');return;}
let b=bounds();if(!b){status('No matching US generator coordinates');return;}
const [[w,s],[e,n]]=b,p=.04;
if(rows.length>150&&e-w>30&&n-s>15&&!$('usGeneratorState').value&&!$('usGeneratorFind').value)b=[[-169,17],[-64,72]];
else b=[[w===e?w-p:w,s===n?s-p:s],[w===e?e+p:e,s===n?n+p:n]];
try{map.fitBounds(b,{padding:Math.max(32,Math.min(70,Math.floor(host.clientWidth/10))),maxZoom:10,duration:0,bearing:0,pitch:0});}catch{map.jumpTo({center:[-98,38],zoom:3});}
queue();}
function inspect(r,focus=false){if(!r)return;selected=r.id;close();const box=$('usGeneratorInspector');box.hidden=false;
box.replaceChildren(E('h3',r.plant+' · generator '+r.generator_id),
 E('p',(r.territory||'United States')+' · '+(r.state||'State unavailable')+(r.county?' · '+r.county:'')),
 E('p',r.technology+' · fuel '+(r.fuel||'not reported')),
 E('p','EIA inventory: '+r.inventory.replace('_',' / ')+' · original status: '+r.status),
 E('p',r.nameplate_mw===null?'Nameplate capacity not supplied':'Reported nameplate capacity '+number(r.nameplate_mw)+' MW · not measured electricity production'),
 E('p','Plant ID '+r.plant_id+' / generator ID '+r.generator_id+' · '+(r.date?'reported date '+r.date:'date not reported')),
 E('p','EIA-860M September 2026 preliminary generator inventory; commissioning or present-day output not independently verified.'));
const link=E('a','Official US EIA data and methodology');link.href=SOURCE;link.target='_blank';link.rel='noopener noreferrer';box.append(link);
if(focus&&map&&active){map.jumpTo({center:r.coordinates,zoom:Math.max(11,map.getZoom())});}queue();}
function bucketClick(bucket){if(bucket.length===1){inspect(bucket[0]);return;}
if(map.getZoom()<13){const box=new window.maplibregl.LngLatBounds();for(const r of bucket)box.extend(r.coordinates);const arr=box.toArray();const [a,b]=arr;const k=.025;map.fitBounds([[a[0]===b[0]?a[0]-k:a[0],a[1]===b[1]?a[1]-k:a[1]],[a[0]===b[0]?b[0]+k:b[0],a[1]===b[1]?b[1]+k:b[1]]],{padding:48,maxZoom:Math.min(15,map.getZoom()+4),duration:0});return;}
close();const panel=E('div');panel.className='atlas-nearby-list';panel.append(E('strong',number(bucket.length)+' nearby generator units'));
for(const r of bucket.slice(0,60)){const b=E('button',r.plant+' · '+r.generator_id+' · '+r.status);b.type='button';b.onclick=()=>inspect(r,true);panel.append(b);}
if(bucket.length>60)panel.append(E('p','Showing first 60 nearby units; narrow filters to inspect more.'));
popup=new window.maplibregl.Popup({maxWidth:'320px'}).setLngLat(bucket[0].coordinates).setDOMContent(panel).addTo(map);}
function paint(){frame=0;clear();if(!active||!map||host.hidden||!toggle.checked||!doc)return;
const canvas=map.getCanvas(),w=canvas.clientWidth,h=canvas.clientHeight,size=map.getZoom()>=13?36:58,bins=new Map();let total=0;
for(const r of rows){const c=map.project(r.coordinates);if(!Number.isFinite(c.x)||!Number.isFinite(c.y)||c.x<0||c.y<0||c.x>w||c.y>h)continue;const key=Math.floor(c.x/size)+':'+Math.floor(c.y/size);if(!bins.has(key))bins.set(key,[]);bins.get(key).push(r);total++;}
for(const bucket of bins.values()){const grouped=bucket.length>1,el=E('button',grouped?number(bucket.length):'');el.type='button';el.className='atlas-us-generator-marker'+(grouped?' cluster':' point');el.dataset.usCount=String(bucket.length);el.dataset.usGenerator=bucket[0].id;el.style.setProperty('--us-color',COLORS[doc.inventory]);el.title=grouped?number(bucket.length)+' US generator units · click to expand':bucket[0].plant+' · '+bucket[0].status;el.setAttribute('aria-label',el.title);if(bucket.some(r=>r.id===selected))el.classList.add('selected');
el.onclick=e=>{e.stopPropagation();bucketClick(bucket);};
const coord=grouped?[bucket.reduce((n,r)=>n+r.coordinates[0],0)/bucket.length,bucket.reduce((n,r)=>n+r.coordinates[1],0)/bucket.length]:bucket[0].coordinates;
markers.push(new window.maplibregl.Marker({element:el,anchor:'center'}).setLngLat(coord).addTo(map));}
host.dataset.usMarkers=String(markers.length);host.dataset.usViewportRecords=String(total);
status(number(rows.length)+' '+doc.inventory.replace('_',' / ')+' units match filters · '+number(total)+' in view · '+number(markers.length)+' visible markers / clusters · preliminary EIA records'+(rows.length&&!total?' · click View US':'')+'.');
}
function queue(){if(!frame)frame=requestAnimationFrame(paint);}
function opts(id,values,caption){const s=$(id);s.replaceChildren(Object.assign(E('option',caption),{value:''}));for(const val of [...new Set(values.filter(Boolean))].sort())s.append(Object.assign(E('option',val),{value:val}));}
function update(){rows=toggle.checked&&doc?filtered(doc.rows,{state:$('usGeneratorState').value,technology:$('usGeneratorTechnology').value,status:$('usGeneratorStage').value,search:$('usGeneratorFind').value}):[];
host.dataset.usRecords=String(rows.length);
const select=$('usGeneratorResults');select.replaceChildren(Object.assign(E('option','Choose generator unit'),{value:''}));
for(const r of rows.slice(0,250))select.append(Object.assign(E('option',r.plant+' · '+r.generator_id+' · '+r.status),{value:r.id}));
status(!toggle.checked?'US generator layer off':failed?'US official dataset currently unavailable; toggle to retry':!doc?'Loading official EIA '+$('usGeneratorInventory').value+' units…':number(rows.length)+' matching '+doc.inventory.replace('_',' / ')+' source units · '+(!active?'Detailed map required':'rendering symbols'));
if(!toggle.checked){clear();close();$('usGeneratorInspector').hidden=true;}queue();}
// Keep up to two validated source partitions for fast inventory switches; completed
// fetch promises must never retain all four inventories indefinitely.
function rememberPart(kind,part){
 cache.delete(kind);cache.set(kind,part);
 while(cache.size>MAX_CACHED_INVENTORIES)cache.delete(cache.keys().next().value);
}
function loadPart(kind){
 if(cache.has(kind)){const data=cache.get(kind);rememberPart(kind,data);return Promise.resolve(data);}
 if(pending.has(kind))return pending.get(kind);
 let request;
 request=window.NordlData.json('data/eia860m/'+kind+'-v1.json').then(d=>validatePart(d,kind)).then(
  part=>{if(pending.get(kind)===request)pending.delete(kind);rememberPart(kind,part);return part;},
  error=>{if(pending.get(kind)===request)pending.delete(kind);throw error;}
 );
 pending.set(kind,request);
 return request;
}
async function load(fit=false){const token=++seq;if(!toggle.checked){doc=null;update();return;}
failed=false;doc=null;close();selected='';update();
const kind=$('usGeneratorInventory').value;
try{
 if(!indexPromise)indexPromise=window.NordlData.json('data/eia860m/index-v1.json').then(validateIndex).catch(e=>{indexPromise=null;throw e;});
 manifest=await indexPromise;
 const part=await loadPart(kind);
 if(token!==seq||!toggle.checked||kind!==$('usGeneratorInventory').value)return;
 doc=part;
 opts('usGeneratorState',part.rows.map(x=>x.state),'All states');
 opts('usGeneratorTechnology',part.rows.map(x=>x.technology),'All technologies');
 opts('usGeneratorStage',part.rows.map(x=>x.status),'All source statuses');
 update();if(fit&&active)viewUS();
}catch(e){if(token===seq){failed=true;doc=null;update();}}
}
function attach(m,on){if(m!==map){map?.off('moveend',queue);map?.off('resize',queue);clear();close();map=m;map?.on('moveend',queue);map?.on('resize',queue);}active=!!on;if(active&&toggle.checked&&!doc)load(true);else update();}
toggle.addEventListener('change',()=>load(true));
$('usGeneratorInventory').addEventListener('change',()=>{
 // Inventory categories have different valid status/technology values.
 // Clear only inventory-specific filters so switching never looks empty
 // because the preceding category had a different EIA status code.
 for(const id of ['usGeneratorState','usGeneratorTechnology','usGeneratorStage'])$(id).value='';
 $('usGeneratorFind').value='';
 $('usGeneratorInspector').hidden=true;
 load(true);
});
for(const id of ['usGeneratorState','usGeneratorTechnology','usGeneratorStage','usGeneratorFind'])$(id).addEventListener(id==='usGeneratorFind'?'input':'change',()=>{close();update();});
$('usGeneratorResults').addEventListener('change',()=>inspect(rows.find(r=>r.id===$('usGeneratorResults').value),true));
$('usGeneratorView').addEventListener('click',viewUS);
window.NordlUsGenerators={attach,getBounds:bounds,getMap:()=>map,getRendered:()=>markers.length,cacheStatus:()=>({cached:[...cache.keys()],pending:[...pending.keys()]})};
})();
