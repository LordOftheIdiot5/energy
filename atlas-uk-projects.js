/* DESNZ October 2026 REPD: planning-register projects, not verified generation. */
(()=>{'use strict';
const FILE='data/uk-repd-projects-v1.json',LICENSE='https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',SOURCE='https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract',SHA='48e76c49f33a1090e78108d1ea9bfe689b35963ea3be1bb4f6516d038a5ff862';
function validate(d){
 if(d?.schema_version!==1||d.release!=='2026-10'||d.published!=='2026-11-13'||d.license!==LICENSE||d.source!==SOURCE||d.source_sha256!==SHA||d.counts?.source_records!==14968||d.counts?.mapped_records!==14388||d.counts?.duplicate_source_rows!==1||!Array.isArray(d.rows)||d.rows.length!==14388)throw Error('UK REPD provenance or count mismatch');
 const seen=new Set();
 for(const r of d.rows){
  const g=r.geometry;
  if(typeof r.id!=='string'||!/^uk-repd-\d+$/.test(r.id)||seen.has(r.id)||r.source_record!==r.id.slice(8)||typeof r.name!=='string'||!r.name.trim()||!['England','Scotland','Wales'].includes(r.country)||typeof r.technology!=='string'||!r.technology.trim()||typeof r.status!=='string'||!r.status.trim()||!Array.isArray(g)||g.length!==2||!g.every(Number.isFinite)||g[0]<-13||g[0]>6||g[1]<48||g[1]>63||(r.reported_mw!==null&&(!Number.isFinite(r.reported_mw)||r.reported_mw<0||r.reported_mw>20000))||'generation_mw' in r||'operational' in r)throw Error('Invalid UK REPD project');
  seen.add(r.id);
 }
 return d;
}
function filtered(rows,{country='',technology='',status='',query=''}={}){
 const q=String(query).trim().toLowerCase();
 return rows.filter(r=>(!country||r.country===country)&&(!technology||r.technology===technology)&&(!status||r.status===status)&&(!q||[r.name,r.id,r.source_record,r.region,r.county].some(v=>String(v??'').toLowerCase().includes(q))));
}
if(typeof module!=='undefined'&&module.exports){module.exports={validate,filtered};return;}
const $=id=>document.getElementById(id),host=$('atlasMap'),toggle=$('globalUkProjects');if(!host||!toggle)return;
const E=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);return e;};
let map=null,active=false,doc=null,request=null,failed=false,rows=[],markers=[],frame=0,selected=null,popup=null;
function clear(){for(const marker of markers)marker.remove();markers=[];host.dataset.ukMarkers='0';host.dataset.ukViewportRecords='0';}
function close(){popup?.remove();popup=null;}
function count(n){return Number(n).toLocaleString('en-GB');}
function inspect(r,focus=false){
 if(!r)return;selected=r.id;close();const box=$('ukProjectInspector');box.hidden=false;
 box.replaceChildren(E('h3',r.name),E('p',r.country+(r.region?' · '+r.region:'')+(r.county?' · '+r.county:'')),E('p',r.technology+' · REPD development status: '+r.status),E('p','Short development status: '+(r.status_short||'Not supplied')),E('p',r.reported_mw===null?'Reported electric capacity not supplied':'Reported project capacity: '+r.reported_mw.toLocaleString('en-GB')+' MW (not verified generation)'),E('p','Official record '+r.source_record+' · updated '+(r.updated||'date not supplied')),E('p','DESNZ October 2026 register; planning and operating statuses are source-reported, not independently verified.'));
 const link=E('a','DESNZ REPD source · OGL v3');link.href=SOURCE;link.target='_blank';link.rel='noopener noreferrer';box.append(link);
 if(focus&&map&&active){map.easeTo({center:r.geometry,zoom:Math.max(10,map.getZoom()),duration:0});}
 schedule();
}
function pickBucket(bucket){
 if(bucket.length===1){inspect(bucket[0]);return;}
 if(map.getZoom()<13){const b=new window.maplibregl.LngLatBounds();for(const r of bucket)b.extend(r.geometry);let [[w,s],[e,n]]=b.toArray();const pad=.015;b.setSouthWest([w===e?w-pad:w,s===n?s-pad:s]);b.setNorthEast([w===e?e+pad:e,s===n?n+pad:n]);map.fitBounds(b,{padding:55,maxZoom:Math.min(15,map.getZoom()+4),duration:0});return;}
 close();const box=E('div');box.className='atlas-nearby-list';box.append(E('strong',count(bucket.length)+' nearby UK project records'));
 for(const r of bucket.slice(0,60)){const button=E('button',r.name+' · '+r.status);button.type='button';button.onclick=()=>inspect(r,true);box.append(button);}
 if(bucket.length>60)box.append(E('p','First 60 records; narrow the filters to inspect more.'));
 popup=new window.maplibregl.Popup({maxWidth:'310px'}).setLngLat(bucket[0].geometry).setDOMContent(box).addTo(map);
}
function draw(){
 frame=0;clear();
 if(!active||!map||host.hidden||!toggle.checked||!doc)return;
 const canvas=map.getCanvas(),w=canvas.clientWidth,h=canvas.clientHeight,cell=map.getZoom()>=13?33:56,bins=new Map();
 let visible=0;
 for(const r of rows){
  const p=map.project(r.geometry);
  if(!Number.isFinite(p.x)||!Number.isFinite(p.y)||p.x<0||p.y<0||p.x>w||p.y>h)continue;
  const k=Math.floor(p.x/cell)+':'+Math.floor(p.y/cell);
  if(!bins.has(k))bins.set(k,[]);
  bins.get(k).push(r);visible++;
 }
 for(const bucket of bins.values()){
  const many=bucket.length>1,el=E('button',many?count(bucket.length):'');
  el.type='button';el.className='atlas-uk-project-marker'+(many?' cluster':' point');el.dataset.ukCount=String(bucket.length);
  el.dataset.ukProject=bucket[0].id;el.title=many?count(bucket.length)+' UK REPD projects · zoom to inspect':bucket[0].name+' · '+bucket[0].status;
  el.setAttribute('aria-label',el.title);if(bucket.some(r=>r.id===selected))el.classList.add('selected');
  el.addEventListener('click',ev=>{ev.stopPropagation();pickBucket(bucket);});
  const coord=many?[bucket.reduce((v,r)=>v+r.geometry[0],0)/bucket.length,bucket.reduce((v,r)=>v+r.geometry[1],0)/bucket.length]:bucket[0].geometry;
  markers.push(new window.maplibregl.Marker({element:el,anchor:'center'}).setLngLat(coord).addTo(map));
 }
 host.dataset.ukMarkers=String(markers.length);host.dataset.ukViewportRecords=String(visible);
 $('ukProjectStatus').textContent=count(rows.length)+' matching REPD records · '+count(visible)+' in view · '+count(markers.length)+' map markers / clusters'+(rows.length&&!visible?' · Use “View UK” or “Fit records”':'')+'. Status and capacity are source-reported.';
}
function schedule(){if(!frame)frame=requestAnimationFrame(draw);}
function update(){
 rows=toggle.checked&&doc?filtered(doc.rows,{country:$('ukProjectCountry').value,technology:$('ukProjectTechnology').value,status:$('ukProjectStage').value,query:$('ukProjectFind').value}):[];
 host.dataset.ukRecords=String(rows.length);
 const sel=$('ukProjectResults');sel.replaceChildren(Object.assign(E('option','Choose UK project'),{value:''}));
 for(const r of rows.slice(0,250))sel.append(Object.assign(E('option',r.name+' · '+r.status),{value:r.id}));
 $('ukProjectStatus').textContent=!toggle.checked?'UK project layer off':failed?'Official UK project archive unavailable; toggle to retry':!doc?'Loading licensed UK REPD project archive…':count(rows.length)+' matching source records · first 250 in selection · '+(!active?'Detailed map required':'loading map symbols');
 if(!toggle.checked){clear();close();$('ukProjectInspector').hidden=true;}
 schedule();
}
function opts(id,values,caption){const select=$(id);select.replaceChildren(Object.assign(E('option',caption),{value:''}));for(const value of [...new Set(values.filter(Boolean))].sort())select.append(Object.assign(E('option',value),{value}));}
async function load(){
 if(!toggle.checked){update();return;}
 if(doc){update();return;}if(request){return;}
 failed=false;update();
 request=window.NordlData.json(FILE).then(validate);
 try{doc=await request;
  opts('ukProjectCountry',doc.rows.map(r=>r.country),'All Great Britain countries');
  opts('ukProjectTechnology',doc.rows.map(r=>r.technology),'All technologies');
  opts('ukProjectStage',doc.rows.map(r=>r.status),'All source development statuses');
 }catch{failed=true;}finally{request=null;update();}
}
function viewUK(){
 if(!map||!active){$('ukProjectStatus').textContent='Open the detailed map to view UK records';return;}
 const bounds=window.NordlEnergyAtlas?.extent(rows.map(r=>r.geometry));
 if(!bounds){$('ukProjectStatus').textContent='No matching UK records to fit';return;}
 const [[w,s],[e,n]]=bounds;map.fitBounds([[w===e?w-.03:w,s===n?s-.03:s],[w===e?e+.03:e,s===n?n+.03:n]],{padding:45,maxZoom:10,duration:0});
}
function attach(m,on){
 if(m!==map){map?.off('moveend',schedule);map?.off('resize',schedule);close();clear();map=m;map?.on('moveend',schedule);map?.on('resize',schedule);}
 active=!!on;
 if(active&&toggle.checked&&!doc&&!request&&!failed)load();else update();
}
toggle.addEventListener('change',load);
for(const id of ['ukProjectCountry','ukProjectTechnology','ukProjectStage','ukProjectFind'])$(id).addEventListener(id==='ukProjectFind'?'input':'change',()=>{close();update();});
$('ukProjectResults').addEventListener('change',()=>inspect(rows.find(r=>r.id===$('ukProjectResults').value),true));
$('ukProjectView').addEventListener('click',viewUK);
window.NordlUkProjects={attach,getBounds:()=>window.NordlEnergyAtlas?.extent(rows.map(r=>r.geometry))||null,getRendered:()=>markers.length};
})();
