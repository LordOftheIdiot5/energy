const assert=require('node:assert/strict'),fs=require('node:fs');
const {validateCatalog,validateRoutes,filterRows,routeLayerFilter,enrich}=require('../atlas-gem-pipelines.js');
const tab=JSON.parse(fs.readFileSync('data/gem-gas-202511/gem-gas-pipelines-202511-v1.json','utf8'));
const geo=JSON.parse(fs.readFileSync('data/gem-gas-202511/gem-gas-pipeline-routes-202511-v1.geojson','utf8'));
assert.equal(validateCatalog(tab),tab);
validateRoutes(geo,new Set(tab.rows.map(r=>r.id)));
const data=enrich(tab,geo);
assert.equal(data.features.length,3921);
const base=routeLayerFilter({status:'operating'},filterRows(tab.rows,{status:'operating'}));
assert.deepEqual(base,['==',['get','status'],'operating']);
assert.ok(JSON.stringify(base).length<90,'Simple status filter must not enumerate 2975 source IDs');
assert.equal(routeLayerFilter(),null,'No filter must preserve all mapped routes');
for(const status of ['construction','proposed','retired','cancelled']){
 const actual=routeLayerFilter({status},filterRows(tab.rows,{status}));
 assert.deepEqual(actual,['==',['get','status'],status]);
}
const match=tab.rows.find(r=>r.start_country&&r.end_country);
assert.ok(match,'Reviewed GEM source should have endpoint countries');
const country=match.start_country;
const countryFilter=routeLayerFilter({country},filterRows(tab.rows,{country}));
assert.deepEqual(countryFilter,['any',['==',['get','start_country'],country],['==',['get','end_country'],country]]);
const combination={status:match.status,country,search:match.id};
const filtered=filterRows(tab.rows,combination);
assert.ok(filtered.some(r=>r.id===match.id),'Native ID search must remain exact');
const combined=routeLayerFilter(combination,filtered);
assert.equal(combined[0],'all');
assert.equal(combined.length,4);
assert.deepEqual(combined[3],['in',['get','pipeline_id'],['literal',filtered.map(r=>r.id)]]);
assert.deepEqual(routeLayerFilter({search:'xx-absent-id'},[]),['in',['get','pipeline_id'],['literal',[]]]);
const oldIds=filterRows(tab.rows,{status:'operating'}).filter(r=>data.features.some(f=>f.properties.pipeline_id===r.id)).map(r=>r.id);
const oldFilter=['in',['get','pipeline_id'],['literal',oldIds]];
const ratio=JSON.stringify(oldFilter).length/JSON.stringify(base).length;
assert.ok(ratio>200,'Compact expression should be orders of magnitude smaller than old 2975-ID filter');
const byId=new Map(tab.rows.map(r=>[r.id,r]));
for(const f of data.features.slice(0,200)){
 const row=byId.get(f.properties.pipeline_id);
 assert.equal(f.properties.status,row.status);
 assert.equal(f.properties.start_country,row.start_country||'');
 assert.equal(f.properties.end_country,row.end_country||'');
}
console.log('PASS GEM compact MapLibre filters: 4246 native records, 3921 routes, status/country/search + unmapped identities; old-to-new expression ratio '+ratio.toFixed(1)+'x');
