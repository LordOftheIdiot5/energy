/* V90.6g: NACEI August 2017, historical reference points only. */
(()=>{'use strict';
const FILE='data/nacei-oilgas-2017-v1.json',SOURCE='https://geoappext.nrcan.gc.ca/arcgis/rest/services/NACEI/energy_infrastructure_of_north_america_en/MapServer',RIGHTS='free and unrestricted with acknowledgement (NACEI)',ATTR='North American Cooperation on Energy Information (NACEI), August 2017';
const EXPECTED={gas_processing:1278,lng_terminals:15,refineries:168};
const COLORS={gas_processing:'#c39d54',lng_terminals:'#5aabc1',refineries:'#b987cf'};
function validate(d){
 if(d?.schema_version!==1||d.source!==SOURCE||d.rights!==RIGHTS||d.attribution!==ATTR||d.source_period!=='2017-08'||!d.layers||!d.rows)throw Error('Unapproved NACEI historic source');
 if(d.layers.refineries?.excluded?.facility_name_not_reported!==141)throw Error('NACEI refinery identities have changed');
 const all=new Set();
 for(const [kind,n] of Object.entries(EXPECTED)){
  const src=d.layers[kind],rows=d.rows[kind];
  if(src?.source_rows!==n||src.mapped_rows!==n||!Array.isArray(rows)||rows.length!==n)throw Error('NACEI historical count regression');
  for(const r of rows){
   const p=r.geometry;
   if(r.kind!==kind||!Number.isInteger(r.source_objectid)||r.id!=='nacei-'+src.layer_id+'-'+r.source_objectid||all.has(r.id)||typeof r.facility!=='string'||!r.facility||typeof r.facility_name_reported!=='boolean'||!['Canada','United States','Mexico'].includes(r.country)||r.status!=='Status not reported in historic source'||!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite)||p[0]<-170||p[0]>-50||p[1]<14||p[1]>74||'operating' in r||'generation' in r)throw Error('Invalid NACEI historic facility');
   all.add(r.id);
  }
 }
 return d;
}
function filter(rows,{country='',search=''}={}){const q=String(search).trim().toLowerCase();return rows.filter(r=>(!country||r.country===country)&&(!q||[r.facility,r.owner,r.operator,r.id,r.city,r.reference_period].some(v=>String(v||'').toLowerCase().includes(q))));}
if(typeof module!=='undefined'&&module.exports){module.exports={validate,filter,EXPECTED};return;}
const $=id=>document.getElementById(id),host=$('atlasMap'),toggle=$('globalNaceiHistoric');if(!host||!toggle)return;
const E=(tag,value)=>{const el=document.createElement(tag);if(value!==undefined)el.textContent=String(value);return el;};
let map=null,active=false,doc=null,loading=null,failed=false,rows=[],markers=[],frame=0,selected='',popup=null;
const display=n=>Number(n).toLocaleString('en-CA');
function clear(){for(const marker of markers)marker.remove();markers=[];host.dataset.naceiMarkers='0';host.dataset.naceiVisible='0';}
function close(){popup?.remove();popup=null;}
function status(s){$('naceiStatus').textContent=s;}
function layer(){return $('naceiKind').value;}
function bounds(){if(!rows.length)return null;let w=Infinity,s=Infinity,e=-Infinity,n=-Infinity;for(const r of rows){const [x,y]=r.geometry;w=Math.min(w,x);e=Math.max(e,x);s=Math.min(s,y);n=Math.max(n,y);}return [[w,s],[e,n]];}
function fit(){if(!active||!map)return;const b=bounds();if(!b){status('No matching historical facility coordinates');return;}const [[w,s],[e,n]]=b,p=.035;map.fitBounds([[w===e?w-p:w,s===n?s-p:s],[w===e?e+p:e,s===n?n+p:n]],{padding:40,maxZoom:10,duration:0,bearing:0,pitch:0});queue();}
function inspect(r,focus=false){
 if(!r)return;selected=r.id;close();const box=$('naceiInspector');box.hidden=false;
 const title=r.facility_name_reported?r.facility:'Official facility name not reported · source ID '+r.source_objectid;
 box.replaceChildren(E('h3',title),E('p',r.country+(r.reference_period?' · source period '+r.reference_period:'')),
 E('p','Reference category: '+r.kind.replace('_',' ')+(r.type?' · '+r.type:'')),
 E('p','Owner at source period: '+(r.owner||'Not reported')+' · Operator: '+(r.operator||'Not reported')),
 E('p',r.reported_capacity===null?'Source capacity not reported':'Historical reported capacity: '+display(r.reported_capacity)+' '+r.capacity_unit),
 E('p','Operational status not reported. This is an August 2017 historical facility reference, NOT confirmation of current operation or ownership.'));
 const link=E('a','Original NACEI official GIS (Canada / USA / Mexico)');link.href=SOURCE;link.rel='noopener noreferrer';link.target='_blank';box.append(link);
 if(focus&&map&&active){map.jumpTo({center:r.geometry,zoom:Math.max(map.getZoom(),10)});}queue();
}
function clickGroup(bucket){
 if(bucket.length===1){inspect(bucket[0]);return;}
 if(map.getZoom()<13){const b=new window.maplibregl.LngLatBounds();for(const row of bucket)b.extend(row.geometry);const [[w,s],[e,n]]=b.toArray(),p=.035;map.fitBounds([[w===e?w-p:w,s===n?s-p:s],[w===e?e+p:e,s===n?n+p:n]],{padding:50,maxZoom:Math.min(15,map.getZoom()+4),duration:0});return;}
 close();const panel=E('div');panel.className='atlas-nearby-list';panel.append(E('strong',display(bucket.length)+' historical facilities'));
 for(const r of bucket.slice(0,40)){const btn=E('button',r.facility);btn.type='button';btn.onclick=()=>inspect(r,true);panel.append(btn);}
 popup=new window.maplibregl.Popup({maxWidth:'300px'}).setLngLat(bucket[0].geometry).setDOMContent(panel).addTo(map);
}
function paint(){
 frame=0;clear();if(!active||!map||host.hidden||!toggle.checked||!doc)return;
 const canvas=map.getCanvas(),w=canvas.clientWidth,h=canvas.clientHeight,cell=map.getZoom()>=13?34:56,bins=new Map();let visible=0;
 for(const r of rows){const p=map.project(r.geometry);if(!Number.isFinite(p.x)||!Number.isFinite(p.y)||p.x<0||p.y<0||p.x>w||p.y>h)continue;const k=Math.floor(p.x/cell)+':'+Math.floor(p.y/cell);if(!bins.has(k))bins.set(k,[]);bins.get(k).push(r);visible++;}
 for(const bucket of bins.values()){
  const many=bucket.length>1,el=E('button',many?display(bucket.length):'');
  el.type='button';el.className='atlas-nacei-marker'+(many?' cluster':' point');
  el.dataset.naceiCount=String(bucket.length);
  el.dataset.naceiRecord=bucket[0].id;
  el.style.setProperty('--nacei-color',COLORS[layer()]);
  el.title=many?display(bucket.length)+' historical NACEI facility records':bucket[0].facility+' · 2017 historical';
  el.setAttribute('aria-label',el.title);if(bucket.some(r=>r.id===selected))el.classList.add('selected');
  el.onclick=e=>{e.stopPropagation();clickGroup(bucket);};
  const xy=many?[bucket.reduce((a,r)=>a+r.geometry[0],0)/bucket.length,bucket.reduce((a,r)=>a+r.geometry[1],0)/bucket.length]:bucket[0].geometry;
  markers.push(new window.maplibregl.Marker({element:el,anchor:'center'}).setLngLat(xy).addTo(map));
 }
 host.dataset.naceiMarkers=String(markers.length);host.dataset.naceiVisible=String(visible);
 status(display(rows.length)+' matching historical '+layer().replace('_',' ')+' records · '+display(visible)+' in map view · '+display(markers.length)+' markers. August 2017; current operation unverified.');
}
function queue(){if(!frame)frame=requestAnimationFrame(paint);}
function selectors(id,values,initial){const s=$(id);s.replaceChildren(Object.assign(E('option',initial),{value:''}));for(const v of [...new Set(values.filter(Boolean))].sort())s.append(Object.assign(E('option',v),{value:v}));}
function update(){
 const kind=layer();rows=toggle.checked&&doc?filter(doc.rows[kind],{country:$('naceiCountry').value,search:$('naceiSearch').value}):[];
 host.dataset.naceiRecords=String(rows.length);
 const s=$('naceiResults');s.replaceChildren(Object.assign(E('option','Choose historic facility'),{value:''}));
 for(const r of rows.slice(0,250))s.append(Object.assign(E('option',r.facility),{value:r.id}));
 status(!toggle.checked?'Historic NACEI layer off':failed?'2017 archive unavailable; turn layer off and on to retry':!doc?'Loading archived North American facilities…':display(rows.length)+' matching August 2017 reference records'+(!active?' · detailed map required':' · drawing symbols'));
 if(!toggle.checked){clear();close();$('naceiInspector').hidden=true;}queue();
}
async function load(){
 if(!toggle.checked){update();return;}if(doc){update();return;}if(loading)return;
 failed=false;update();loading=window.NordlData.json(FILE).then(validate);
 try{doc=await loading;selectors('naceiCountry',Object.values(doc.rows).flat().map(r=>r.country),'All countries');}catch{failed=true;}finally{loading=null;update();}
}
function attach(m,on){if(map!==m){map?.off('moveend',queue);map?.off('resize',queue);clear();close();map=m;map?.on('moveend',queue);map?.on('resize',queue);}active=!!on;if(active&&toggle.checked&&!doc&&!loading)load();else update();}
toggle.addEventListener('change',()=>{if(toggle.checked)load();else update();});
$('naceiKind').addEventListener('change',()=>{$('naceiSearch').value='';$('naceiCountry').value='';$('naceiInspector').hidden=true;close();update();});
for(const id of ['naceiCountry','naceiSearch'])$(id).addEventListener(id==='naceiSearch'?'input':'change',()=>{close();update();});
$('naceiResults').addEventListener('change',()=>inspect(rows.find(r=>r.id===$('naceiResults').value),true));
$('naceiView').addEventListener('click',fit);
window.NordlNaceiAtlas={attach,getBounds:bounds,getRendered:()=>markers.length};
})();