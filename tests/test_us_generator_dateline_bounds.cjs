const assert=require('node:assert/strict'),fs=require('node:fs');
const {validateIndex,validatePart,filtered,sourceBounds,PARTS}=require('../atlas-us-generators.js');

function same(a,b){assert.deepEqual(a,b);}
same(sourceBounds([]),null);
same(sourceBounds([{coordinates:[145,13]}]),[[145,13],[145,13]]);
same(sourceBounds([{coordinates:[-120,30]},{coordinates:[-70,48]}]),[[-120,30],[-70,48]]);
same(sourceBounds([{coordinates:[179,15]},{coordinates:[-179,20]}]),[[179,15],[181,20]]);
same(sourceBounds([{coordinates:[-179,21]},{coordinates:[179,16]},{coordinates:[170,18]}]),[[170,16],[181,21]]);
same(sourceBounds([{coordinates:[145,14]},{coordinates:[-170,51]}]),[[145,14],[190,51]]);
same(sourceBounds([{coordinates:[-160,14]},{coordinates:[-60,45]},{coordinates:[-155,25]}]),[[-160,14],[-60,45]]);
same(sourceBounds([{coordinates:[null,3]},{coordinates:[Infinity,4]}]),null);
same(sourceBounds([{coordinates:[0,0]},{coordinates:[0,0]}]),[[0,0],[0,0]]);

const all=JSON.parse(fs.readFileSync('data/eia860m-generators-v1.json','utf8'));
assert.equal(all.rows.length,40048);
const positive=all.rows.filter(r=>r.coordinates[0]>0);
const negative=all.rows.filter(r=>r.coordinates[0]<0);
assert.equal(positive.length+negative.length,all.rows.length);
assert.ok(negative.length>0);
if(positive.length){
 const bounds=sourceBounds(positive);
 assert.ok(bounds[0][0]>0&&bounds[1][0]<=180,'Positive longitude territory must have a viewable local extent');
 const example=positive[0];
 assert.deepEqual(filtered(all.rows,{state:example.state,search:example.id}).map(r=>r.id),[example.id]);
}
const every=sourceBounds(all.rows);
assert.ok(every&&every[1][0]-every[0][0]<360,'Global geography never requires >360-degree fit');
assert.ok(all.rows.every(r=>r.coordinates.length===2),'No derived position inventions');
console.log('PASS source longitude bounds',JSON.stringify({
 nativeGeneratorUnits:all.rows.length,positiveLongitudeUnits:positive.length,
 negativeLongitudeUnits:negative.length,allSourceBounds:every,
 datelineTwoPointBounds:sourceBounds([{coordinates:[179,15]},{coordinates:[-179,20]}])
}));
