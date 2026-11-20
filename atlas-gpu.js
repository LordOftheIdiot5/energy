/* Opt-in GPU layer on the existing map. The viewport renderer stays authoritative on failure or text search. */
(()=>{'use strict';const $=id=>document.getElementById(id),host=$('atlasMap'),opt=$('globalGpu'),status=$('globalGpuStatus');
if(!host||!opt)return;
const SRC='nordl-wri-vector',layers=['nordl-wri-clusters','nordl-wri-detail'],geo='nordl-world-geo',border='nordl-world-border',baseLayers=['nordl-world-ocean','nordl-world-land','nordl-world-coast','nordl-world-borders'];
const colors={Solar:'#f5ca60',Wind:'#46d9e1',Hydro:'#559dff',Nuclear:'#49df9c',Gas:'#b58eff',Coal:'#b7bec8',Oil:'#e8868e',Biomass:'#a4d77e',Geothermal:'#f3a367',Waste:'#d4a9ed',Storage:'#e896ce'};
let map=null,ready=false,loading=false,failed=false,protocol=null,seq=0,timer=null,context=null,library=null,signature='',worldShown=null,visible=null;
function notify(){window.dispatchEvent(new Event('atlas:gpu-state'));}
function dispose(){clearTimeout(timer);if(map){for(const id of [...layers,...baseLayers])if(map.getLayer(id))map.removeLayer(id);for(const id of [SRC,geo,border])if(map.getSource(id))map.removeSource(id);}ready=false;loading=false;signature='';worldShown=null;visible=null;host.dataset.gpuSymbols='0';}
function fail(message){seq++;failed=true;dispose();status.textContent=message+' · using standard map';notify();}
function libraryLoad(){if(window.pmtiles)return Promise.resolve();if(library)return library;library=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/pmtiles@4.5.0/dist/pmtiles.js';const t=setTimeout(()=>{s.remove();reject(Error('PMTiles library timeout'));},12000);s.onload=()=>{clearTimeout(t);window.pmtiles?resolve():reject(Error('PMTiles unavailable'));};s.onerror=()=>{clearTimeout(t);s.remove();reject(Error('PMTiles unavailable'));};document.head.append(s);}).catch(e=>{library=null;throw e;});return library;}
async function json(path){const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error('Missing tile or geography data');return r.json();}
function filterExpression(c){const tests=['all'];if(c.fuel)tests.push(['==',['get','fuel'],c.fuel]);if(c.country)tests.push(['==',['get','country'],c.country]);const bands={10:['10-99','100-999','1000+'],100:['100-999','1000+'],1000:['1000+']};if(c.min)tests.push(['in',['get','capacity_band'],['literal',bands[c.min]||[]]]);return tests.length>1?tests:null;}
function wanted(){return !!(context?.active&&context.enabled&&opt.checked&&!context.query&&!failed&&context.count>0);}
function apply(){if(!map||!map.getSource(SRC))return;const show=wanted(),world=show&&context.world&&map.getZoom()<=2.4;
const key=JSON.stringify([context?.fuel,context?.country,context?.min]);if(key!==signature){signature=key;for(const id of layers)map.setFilter(id,filterExpression(context));}
if(visible!==show){visible=show;for(const id of layers)map.setLayoutProperty(id,'visibility',show?'visible':'none');}
if(worldShown!==world){worldShown=world;for(const id of baseLayers)map.setLayoutProperty(id,'visibility',world?'visible':'none');}}
async function init(){if(loading||ready||!wanted()||!map)return;loading=true;const token=++seq,m=map;status.textContent='Checking vector delivery…';
try{const [manifest,land,borders]=await Promise.all([json('data/atlas-tiles/index-v1.json'),json('data/atlas-world-land-v512.json'),json('data/atlas-world-borders-v512.json'),libraryLoad()]);
if(token!==seq||m!==map||!wanted())return;
if(manifest.schema_version!==1||manifest.delivery!=='same-origin-static'||manifest.status!=='experimental_delivery'||manifest.license!=='https://creativecommons.org/licenses/by/4.0/'||!/^wri-v130-[a-f0-9]{64}\.pmtiles$/.test(manifest.path)||manifest.path!=='wri-v130-'+manifest.archive_sha256+'.pmtiles'||manifest.source_release!=='1.3.0 (2021 historical)'||manifest.source_records!==context.total||!Number.isInteger(manifest.archive_bytes)||manifest.archive_bytes<256||manifest.archive_bytes>25000000||land.version!=='5.1.2'||borders.release!=='5.1.2')throw Error('Invalid tile manifest');
const url=new URL('data/atlas-tiles/'+manifest.path,location.href).href;
const check=await fetch(url,{headers:{Range:'bytes=0-126'},cache:'no-cache'});if(check.status!==206||check.headers.get('Content-Range')!=='bytes 0-126/'+manifest.archive_bytes){check.body?.cancel();throw Error('Byte-range delivery unavailable');}const bytes=new Uint8Array(await check.arrayBuffer());if(bytes.length!==127||String.fromCharCode(...bytes.slice(0,7))!=='PMTiles'||bytes[7]!==3)throw Error('Invalid archive header');
if(token!==seq||m!==map||!wanted())return;
if(!protocol){protocol=new window.pmtiles.Protocol();window.maplibregl.addProtocol('pmtiles',protocol.tile);}
map.addSource(geo,{type:'geojson',data:{type:'FeatureCollection',features:land.polygons.map(p=>({type:'Feature',geometry:{type:'Polygon',coordinates:p},properties:{}}))},attribution:'Natural Earth v5.1.2 · public domain'});map.addSource(border,{type:'geojson',data:borders});
const light=document.body.dataset.theme==='light';const before=map.getLayer('energy-zone-fill')?'energy-zone-fill':undefined;
for(const layer of [{id:baseLayers[0],type:'background',paint:{'background-color':light?'#dce8ef':'#0a1521'}},{id:baseLayers[1],type:'fill',source:geo,paint:{'fill-color':light?'#b6cbd1':'#243a48'}},{id:baseLayers[2],type:'line',source:geo,paint:{'line-color':light?'#849da7':'#486172','line-width':.7}},{id:baseLayers[3],type:'line',source:border,paint:{'line-color':light?'#78909c':'#6a8190','line-opacity':.65,'line-width':.7}}])map.addLayer({...layer,layout:{visibility:'none'}},before);
map.addSource(SRC,{type:'vector',url:'pmtiles://'+url,attribution:manifest.attribution+' · CC BY 4.0'});
for(const [i,id] of layers.entries())map.addLayer({id,type:'circle',source:SRC,'source-layer':i?'plants':'plant_clusters',minzoom:i?5:0,maxzoom:i?24:5,layout:{visibility:'none'},paint:{'circle-color':['match',['get','fuel'],...Object.entries(colors).flat(),'#8599ad'],'circle-radius':i?['interpolate',['linear'],['coalesce',['get','capacity_mw'],0],0,2.7,100,4.2,1000,7,5000,11]:['interpolate',['linear'],['get','count'],1,2,10,3.5,100,7,1000,12],'circle-opacity':.83,'circle-stroke-width':.5,'circle-stroke-color':'#101a25'}});
apply();timer=setTimeout(()=>{if(!ready)fail('Vector render timed out');},20000);
}catch(e){if(token===seq)fail(e.message||'GPU unavailable');}finally{if(token===seq)loading=false;}}
function inspect(e){if(!ready||!wanted())return;const f=map.queryRenderedFeatures(e.point,{layers});if(!f.length)return;const p=f[0].properties;if(p.id){context.inspect(p.id);}else{map.easeTo({center:e.lngLat,zoom:Math.max(5,map.getZoom()+2)});}}
function render(){if(!map||!wanted()||!map.getLayer(layers[0]))return;let n;try{n=map.queryRenderedFeatures({layers}).length;}catch{return;}host.dataset.gpuSymbols=String(n);if(n>0&&!ready){ready=true;clearTimeout(timer);status.textContent='GPU vector mode · historical power plants';notify();}}
function error(e){if(e.sourceId===SRC||String(e.error?.message||'').includes('pmtiles://'))fail('Vector tiles unavailable');}
function detach(){if(!map)return;map.off('idle',render);map.off('render',render);map.off('error',error);map.off('click',inspect);seq++;dispose();}
function sync(m,c){if(map!==m){detach();map=m;failed=false;if(map){map.on('idle',render);map.on('render',render);map.on('error',error);map.on('click',inspect);}}context=c;
if(!wanted()){if(loading){seq++;dispose();}apply();if(!opt.checked)status.textContent='Standard map selected';else if(c.query)status.textContent='Text search uses standard map';else if(!c.count)status.textContent='No matching records';return false;}
if(!map?.getSource(SRC)&&!loading&&!ready)init();apply();return ready&&wanted();}
opt.addEventListener('change',()=>{failed=false;if(!opt.checked){seq++;dispose();}notify();});
window.NordlAtlasGpu={sync};
})();
