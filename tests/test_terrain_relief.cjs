const assert=require('node:assert/strict');
const {setRelief,SOURCE,LAYER}=require('../terrain-relief.js');
const sources=new Map(),layers=new Map();
const map={getStyle:()=>({layers:[{id:'land',type:'fill'},{id:'labels',type:'symbol'},{id:'asset-polygons',type:'fill'}]}),getSource:k=>sources.get(k),getLayer:k=>layers.get(k),addSource:(k,v)=>sources.set(k,v),removeSource:k=>sources.delete(k),addLayer:(v,before)=>{assert.equal(before,'labels');layers.set(v.id,v);},removeLayer:k=>layers.delete(k)};
assert.equal(setRelief(map,true),true);assert.equal(sources.get(SOURCE).encoding,'terrarium');assert.equal(layers.get(LAYER).type,'hillshade');assert.equal(setRelief(map,true),true);assert.equal(sources.size,1);assert.equal(setRelief(map,false),false);assert.equal(layers.size,0);assert.equal(sources.size,0);
console.log('Relief activation, attribution, layer order and cleanup passed');
