/* GEM November 2025 simplified global gas transmission lines, CC BY 4.0 */
(()=>{'use strict';
const ROOT='data/gem-gas-202511/',TABLE=ROOT+'gem-gas-pipelines-202511-v1.json',GEO=ROOT+'gem-gas-pipeline-routes-202511-v1.geojson';
const ATTR='Data: Global Gas Infrastructure Tracker, Global Energy Monitor, November 2025',LICENSE='https://creativecommons.org/licenses/by/4.0/';
const TSHA='33cf8df6a6ba9bfaad0fd6c046b8b0be6d746bba014c7e31cd6b4618ed1605f1',GSHA='d2d940433656e58ba32a852aba6f30300846ab52375b0139f02df88d691f4378';
const STATUS={operating:2975,construction:282,proposed:611,idle:8,cancelled:243,shelved:103,mothballed:9,retired:14,'Status not reported':1};
const SOURCE='https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker';
const COLORS={operating:'#52d2ae',construction:'#e9b755',proposed:'#61b2ed',idle:'#b3b7c6',cancelled:'#d96a78',shelved:'#9d8db5',mothballed:'#8993a3',retired:'#85848e','Status not reported':'#e6a18d'};
const IDS=['nordl-gem-gas-routes','nordl-gem-gas-highlight'],SRC='nordl-gem-gas-lines',HIGHLIGHT='nordl-gem-gas-selected';
function validateCatalog(d){
 if(d?.schema_version!==1||d.release!=='2025-11'||d.license!=='CC BY 4.0'||d.license_url!==LICENSE||d.attribution!==ATTR||d.table_sha256!==TSHA||d.routes_sha256!==GSHA||d.dataset!=='GEM global gas transmission pipelines'||d.source_rows!==4246||d.mapped_routes!==3921||!Array.isArray(d.rows)||d.rows.length!==4246)throw Error('GEM catalog provenance mismatch');
 const seen=new Set(),counts={};
 for(const r of d.rows){if(typeof r.id!=='string'||!r.id||seen.has(r.id)||typeof r.name!=='string'||!r.name||r.data_source!==ATTR||!Object.hasOwn(STATUS,r.status)||'operating_now' in r||'surveyed_route' in r)throw Error('Invalid GEM pipeline identity/status');seen.add(r.id);counts[r.status]=(counts[r.status]||0)+1;}
 for(const [k,count] of Object.entries(STATUS))if(counts[k]!==count||d.statuses[k]!==count)throw Error('GEM source status count changed');
 return d;
}
function validateRoutes(d,ids){
 if(d?.type!=='FeatureCollection'||d.schema_version!==1||d.release!=='2025-11'||d.attribution!==ATTR||d.license_url!==LICENSE||d.table_sha256!==TSHA||d.routes_sha256!==GSHA||!Array.isArray(d.features)||d.features.length!==3921)throw Error('GEM route archive provenance changed');
 const seen=new Set();
 for(const f of d.features){
  const id=f.properties?.pipeline_id,g=f.geometry;
  if(!ids.has(id)||seen.has(id)||g?.type!=='MultiLineString'||!Array.isArray(g.coordinates)||!g.coordinates.length)throw Error('GEM route identity/geometry mismatch');
  seen.add(id);
  for(const line of g.coordinates){if(!Array.isArray(line)||line.length<2)throw Error('Incomplete GEM route line');
   for(const point of line){if(!Array.isArray(point)||point.length<2||!point.slice(0,2).every(Number.isFinite)||Math.abs(point[0])>180||Math.abs(point[1])>90)throw Error('Invalid GEM route coordinate');}
  }
 }
 return d;
}
function filterRows(rows,{status='',country='',search=''}={}){
 const q=String(search||'').trim().toLowerCase();
 return rows.filter(r=>(!status||r.status===status)&&(!country||[r.start_country,r.end_country].includes(country))&&(!q||[r.id,r.name,r.start_place,r.end_place,r.start_country,r.end_country,r.countries].some(s=>String(s??'').toLowerCase().includes(q))));
}
function enrich(tab,geo){
 const byId=new Map(tab.rows.map(r=>[r.id,r]));return {type:'FeatureCollection',features:geo.features.map(f=>{
  const r=byId.get(f.properties.pipeline_id);if(!r)throw Error('Unmatched source line');
  return {type:'Feature',geometry:f.geometry,properties:{pipeline_id:r.id,status:r.status,
   start_country:r.start_country||'',end_country:r.end_country||'',color:COLORS[r.status]}};
 })};
}
if(typeof module!=='undefined'&&module.exports){module.exports={validateCatalog,validateRoutes,filterRows,enrich,STATUS};return;}
const $=id=>document.getElementById(id),host=$('atlasMap'),opt=$('globalGemPipelines');if(!host||!opt)return;
const node=(tag,v)=>{const el=document.createElement(tag);if(v!==undefined)el.textContent=String(v);return el;};
let map=null,active=false,catalog=null,routeData=null,features=null,fetchPromise=null,failed=false,filtered=[],byId=new Map(),routeIds=new Set(),highlight=null,selected='',loadToken=0;
function stat(msg){$('gemPipelineStatus').textContent=msg;}
const display=n=>Number(n).toLocaleString('en-GB');
function selectedClear(){selected='';if(map?.getSource(HIGHLIGHT))map.getSource(HIGHLIGHT).setData({type:'FeatureCollection',features:[]});}
function dispose(m){if(!m)return;try{m.off('click',IDS[0],onClick);m.off('mouseenter',IDS[0],enter);m.off('mouseleave',IDS[0],leave);for(const id of IDS)if(m.getLayer(id))m.removeLayer(id);for(const id of [HIGHLIGHT,SRC])if(m.getSource(id))m.removeSource(id);}catch{}}
function enter(){if(map)map.getCanvas().style.cursor='pointer';}function leave(){if(map)map.getCanvas().style.cursor='';}
function onClick(e){const hit=e.features?.[0],record=byId.get(hit?.properties?.pipeline_id);if(record)inspect(record,false);}
function inspector(row){
 const box=$('gemPipelineInspector');box.hidden=false;box.replaceChildren(
  node('h3',row.name),
  node('p','GEM pipeline status: '+row.status+' (November 2025 source-reported)'),
  node('p','Start: '+(row.start_place||'Not reported')+' · '+(row.start_country||'Country not reported')),
  node('p','End: '+(row.end_place||'Not reported')+' · '+(row.end_country||'Country not reported')),
  node('p',row.length_km==null?'Route length not reported':'Reported pipeline length: '+display(row.length_km)+' km (method: '+(row.length_basis||'not specified')+')'),
  node('p',row.capacity_bcm_y==null?'Capacity not reported':'Reported design capacity: '+display(row.capacity_bcm_y)+' billion m³/year'),
  node('p',routeIds.has(row.id)?'Simplified mapped route exists; geometry may be approximate.':'No mapped route supplied. This record is listed without an invented line.'),
  node('p','Global Energy Monitor, November 2025 · CC BY 4.0. Status is not confirmation of current operation, and mapped lines are not survey-accurate.'));
 const a=node('a','Global Energy Monitor source · CC BY 4.0');a.href=SOURCE;a.target='_blank';a.rel='noopener noreferrer';box.append(a);
 if(row.source_url&&/^https:\/\//.test(row.source_url)){const link=node('a','Original pipeline source record');link.href=row.source_url;link.target='_blank';link.rel='noopener noreferrer';box.append(link);}
}
function routeBounds(feat){
 let w=Infinity,s=Infinity,e=-Infinity,n=-Infinity;
 for(const line of feat.geometry.coordinates)for(const p of line){w=Math.min(w,p[0]);e=Math.max(e,p[0]);s=Math.min(s,p[1]);n=Math.max(n,p[1]);}
 return Number.isFinite(w)?[[w,s],[e,n]]:null;
}
function showBounds(b){if(!map||!active||!b)return;const [[w,s],[e,n]]=b;
 if(e-w>290||n-s>125){map.jumpTo({center:[0,20],zoom:Math.max(map.getMinZoom(),1),bearing:0,pitch:0});return;}
 const pad=.07;try{map.fitBounds([[w===e?w-pad:w,s===n?s-pad:s],[w===e?e+pad:e,s===n?n+pad:n]],{padding:40,maxZoom:12,duration:0,bearing:0,pitch:0});}catch{map.jumpTo({center:[(w+e)/2,(s+n)/2],zoom:2});}}
function inspect(row,zoom=true){
 if(!row)return;selected=row.id;inspector(row);
 const feature=features?.features.find(x=>x.properties.pipeline_id===row.id);
 if(map?.getSource(HIGHLIGHT))map.getSource(HIGHLIGHT).setData(feature?{type:'FeatureCollection',features:[feature]}:{type:'FeatureCollection',features:[]});
 if(zoom&&feature)showBounds(routeBounds(feature));
 if(!feature)stat('Pipeline record '+row.id+' has no mapped route in the November 2025 source. No coordinates inferred.');
}
function getBounds(){
 if(!filtered.length||!features)return null;
 const ids=new Set(filtered.map(r=>r.id));let w=Infinity,s=Infinity,e=-Infinity,n=-Infinity;
 for(const f of features.features){if(!ids.has(f.properties.pipeline_id))continue;for(const line of f.geometry.coordinates)for(const p of line){w=Math.min(w,p[0]);e=Math.max(e,p[0]);s=Math.min(s,p[1]);n=Math.max(n,p[1]);}}
 return Number.isFinite(w)?[[w,s],[e,n]]:null;
}
function fit(){if(!active||!map){stat('Switch to the detailed map first');return;}if(!features){stat('Enable the route layer to load the data');return;}const bounds=getBounds();if(!bounds){stat('No mapped routes match these filters; use the directory search');return;}showBounds(bounds);}
function populate(id,items,placeholder){const s=$(id);s.replaceChildren(Object.assign(node('option',placeholder),{value:''}));for(const x of [...new Set(items.filter(Boolean))].sort())s.append(Object.assign(node('option',x),{value:x}));}
function update(){
 filtered=opt.checked&&catalog?filterRows(catalog.rows,{status:$('gemStatus').value,country:$('gemCountry').value,search:$('gemSearch').value}):[];
 host.dataset.gemRecords=String(filtered.length);
 const choices=$('gemResults');choices.replaceChildren(Object.assign(node('option','Choose pipeline record'),{value:''}));
 for(const r of filtered.slice(0,250))choices.append(Object.assign(node('option',r.name+' · '+r.status),{value:r.id}));
 const mapped=filtered.filter(r=>routeIds.has(r.id)).length;
 host.dataset.gemMatchingRoutes=String(mapped);
 if(map?.getLayer(IDS[0])){
  const visible=!!(opt.checked&&active&&features);
  for(const id of IDS)map.setLayoutProperty(id,'visibility',visible?'visible':'none');
  if(visible){const filter=['in',['get','pipeline_id'],['literal',filtered.filter(r=>routeIds.has(r.id)).map(r=>r.id)]];
   map.setFilter(IDS[0],filter);}
 }
 stat(!opt.checked?'Global gas pipeline layer off':failed?'GEM 2025 archive unavailable; switch off and on to retry':!catalog?'Loading licensed pipeline data and simplified routes…':
  display(filtered.length)+' pipeline records · '+display(mapped)+' mapped routes · November 2025 GEM tracker, CC BY 4.0 · simplified lines, current operating status unverified.');
 if(!opt.checked){selectedClear();$('gemPipelineInspector').hidden=true;}
}
function initialize(){
 if(!map||!active||!features||map.getSource(SRC))return;
 try{
  map.addSource(SRC,{type:'geojson',data:features,attribution:'Global Energy Monitor, Global Gas Infrastructure Tracker, November 2025 · CC BY 4.0'});
  map.addSource(HIGHLIGHT,{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:IDS[0],source:SRC,type:'line',
    layout:{'line-cap':'round','line-join':'round'},
    paint:{'line-color':['get','color'],'line-opacity':.78,'line-width':['interpolate',['linear'],['zoom'],0,.6,4,1.4,8,3.5,12,6]}});
  map.addLayer({id:IDS[1],source:HIGHLIGHT,type:'line',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':'#fff3c4','line-opacity':.98,'line-width':['interpolate',['linear'],['zoom'],0,2,7,5,12,10]}});
  map.on('click',IDS[0],onClick);map.on('mouseenter',IDS[0],enter);map.on('mouseleave',IDS[0],leave);
  host.dataset.gemRenderedFeatures=String(features.features.length);update();
 }catch{failed=true;dispose(map);stat('MapLibre pipeline layer unavailable; existing infrastructure layers remain visible.');}
}
async function load(){
 if(!opt.checked){update();return;}
 if(catalog&&features){initialize();update();return;}
 if(fetchPromise)return;
 failed=false;update();const token=++loadToken;
 fetchPromise=Promise.all([window.NordlData.json(TABLE),window.NordlData.json(GEO)]);
 try{let [t,g]=await fetchPromise;validateCatalog(t);const ids=new Set(t.rows.map(r=>r.id));validateRoutes(g,ids);
  if(token!==loadToken||!opt.checked)return;
  catalog=t;routeData=g;byId=new Map(t.rows.map(r=>[r.id,r]));features=enrich(t,g);routeIds=new Set(g.features.map(f=>f.properties.pipeline_id));
  populate('gemCountry',t.rows.flatMap(r=>[r.start_country,r.end_country]),'All endpoint countries');
  initialize();update();
 }catch{if(token===loadToken){failed=true;stat('Licensed pipeline data unavailable or failed validation; other map layers unchanged.');}}
 finally{fetchPromise=null;}
}
function attach(m,on){
 if(m!==map){dispose(map);map=m;host.dataset.gemRenderedFeatures='0';}
 active=!!on;if(active&&opt.checked)load();else update();
}
opt.addEventListener('change',()=>{if(opt.checked)load();else update();});
for(const id of ['gemStatus','gemCountry','gemSearch'])$(id).addEventListener(id==='gemSearch'?'input':'change',()=>{selectedClear();update();});
$('gemResults').addEventListener('change',()=>inspect(byId.get($('gemResults').value),true));
$('gemView').addEventListener('click',fit);
window.NordlGemPipelines={attach,getBounds,renderCount:()=>map?.getLayer(IDS[0])?features?.features.length||0:0};
})();
