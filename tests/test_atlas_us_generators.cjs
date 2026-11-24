const assert=require('node:assert/strict'),fs=require('node:fs');
const {validateIndex,validatePart,filtered,PARTS}=require('../atlas-us-generators.js');
const d=JSON.parse(fs.readFileSync('data/eia860m-generators-v1.json','utf8'));
assert.equal(d.rows.length,40048);
assert.equal(d.counts.source_rows,40163);
assert.equal(Object.values(PARTS).reduce((a,b)=>a+b,0),40048);
const bins=Object.fromEntries(Object.keys(PARTS).map(id=>[id,d.rows.filter(r=>r.inventory===id)]));
const index={schema_version:1,release:'2026-09',published:'2026-10-23',source:d.source,rights:d.rights,source_sha256:d.source_sha256,counts:d.counts,inventories:Object.entries(PARTS).map(([id,records])=>({id,records,path:'data/eia860m/'+id+'-v1.json',sha256:'0'.repeat(64)}))};
assert.equal(validateIndex(index),index);
for(const [kind,rows] of Object.entries(bins)){
 const part={schema_version:1,release:'2026-09',source:d.source,rights:d.rights,inventory:kind,source_sha256:d.source_sha256,rows};
 assert.equal(validatePart(part,kind),part);
 assert.equal(part.rows.length,PARTS[kind]);
 assert.ok(rows.every(r=>!('generation_mw' in r)&&!('is_operational' in r)));
}
const planned=bins.planned, sample=planned.find(r=>r.state==='AZ'&&r.technology==='Solar Photovoltaic');
assert.ok(sample);const hit=filtered(planned,{state:sample.state,technology:sample.technology,status:sample.status,search:sample.id});
assert.equal(hit.length,1);assert.equal(hit[0].id,sample.id);
assert.equal(filtered(planned,{search:'nonexistent_does_not_exist_123'}).length,0);
assert.throws(()=>validateIndex({...index,source_sha256:'unapproved'}));
assert.throws(()=>validatePart({...bins,rows:planned.slice(1),inventory:'planned'},'planned'));
const broken={schema_version:1,release:'2026-09',source:d.source,rights:d.rights,inventory:'planned',source_sha256:d.source_sha256,rows:[{...planned[0],is_operational:true},...planned.slice(1)]};
assert.throws(()=>validatePart(broken,'planned'));
console.log('PASS EIA 860M full 40,048 source records, four categories, identities, statuses, filters and forbidden inferred generation');
