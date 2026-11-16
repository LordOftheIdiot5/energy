(()=>{'use strict';
const SOURCE='nordl-relief-elevation',LAYER='nordl-relief-hillshade';
function setRelief(map,enabled){
 if(!enabled){if(map.getLayer(LAYER))map.removeLayer(LAYER);if(map.getSource(SOURCE))map.removeSource(SOURCE);return false;}
 if(map.getLayer(LAYER))return true;
 const layers=map.getStyle()?.layers||[];
 const before=layers.find(x=>x.type==='symbol'||x.id==='asset-polygons')?.id;
 try{
  if(!map.getSource(SOURCE))map.addSource(SOURCE,{type:'raster-dem',tiles:['https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'],encoding:'terrarium',tileSize:512,maxzoom:12,attribution:'<a href="https://mapterhorn.com/attribution/">© Mapterhorn and elevation data providers</a>'});
  map.addLayer({id:LAYER,type:'hillshade',source:SOURCE,paint:{'hillshade-exaggeration':.45,'hillshade-shadow-color':'#56616c','hillshade-highlight-color':'#ffffff','hillshade-accent-color':'#7e8991'}},before);
  return true;
 }catch(error){if(map.getLayer(LAYER))map.removeLayer(LAYER);if(map.getSource(SOURCE))map.removeSource(SOURCE);throw error;}
}
if(typeof module!=='undefined'&&module.exports)module.exports={setRelief,SOURCE,LAYER};else window.NordlRelief={setRelief,SOURCE,LAYER};
})();