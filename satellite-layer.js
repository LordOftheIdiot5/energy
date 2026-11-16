(()=>{'use strict';
const SOURCE='nordl-satellite-2016',LAYER='nordl-satellite-raster';
const TILE='https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg';
const CREDIT='EOxCloudless <a href="https://cloudless.eox.at/">https://cloudless.eox.at</a> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 &amp; 2017) · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>';
function setSatellite(map,enabled){
 if(!enabled){if(map.getLayer(LAYER))map.removeLayer(LAYER);if(map.getSource(SOURCE))map.removeSource(SOURCE);return false;}
 if(map.getLayer(LAYER))return true;
 const layers=map.getStyle()?.layers||[];
 const before=layers.find(x=>x.id==='nordl-relief-hillshade'||x.type==='symbol'||x.id==='asset-polygons')?.id;
 try{map.addSource(SOURCE,{type:'raster',tiles:[TILE],tileSize:256,minzoom:0,maxzoom:13,attribution:CREDIT});
 map.addLayer({id:LAYER,type:'raster',source:SOURCE,paint:{'raster-opacity':1,'raster-fade-duration':0}},before);return true;}
 catch(e){if(map.getLayer(LAYER))map.removeLayer(LAYER);if(map.getSource(SOURCE))map.removeSource(SOURCE);throw e;}
}
if(typeof module!=='undefined'&&module.exports)module.exports={setSatellite,SOURCE,LAYER,TILE,CREDIT};else window.NordlSatellite={setSatellite,SOURCE,LAYER};
})();