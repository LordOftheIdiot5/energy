(()=>{'use strict';
const SOURCE='nve-published-grid',LAYER='nve-published-grid-overlay';
const ROOT='https://kart.nve.no/enterprise/rest/services/Nettanlegg5/MapServer';
const MODES=Object.freeze({transmission:'0',regional:'1',cables:'2',stations:'4',all:'0,1,2,4'});
function tile(mode){
 if(!Object.hasOwn(MODES,mode))throw Error('Unknown public grid layer');
 return ROOT+'/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&layers=show:'+MODES[mode]+'&f=image';
}
function setGrid(map,mode){
 if(mode!=='off'&&!Object.hasOwn(MODES,mode))throw Error('Unknown public grid layer');
 if(map.getLayer(LAYER))map.removeLayer(LAYER);
 if(map.getSource(SOURCE))map.removeSource(SOURCE);
 if(mode==='off')return false;
 const before=map.getLayer('energy-flows')?'energy-flows':undefined;
 try{map.addSource(SOURCE,{type:'raster',tiles:[tile(mode)],tileSize:256,minzoom:4,maxzoom:11,bounds:[3,55,33,73],attribution:'<a href="https://kart.nve.no/enterprise/rest/services/Nettanlegg5/MapServer">NVE · Nettanlegg utbygd</a> / <a href="https://data.norge.no/nlod/en/1.0">NLOD 1.0</a>'});
 map.addLayer({id:LAYER,type:'raster',source:SOURCE,paint:{'raster-opacity':.9,'raster-fade-duration':0}},before);return true;}
 catch(e){if(map.getLayer(LAYER))map.removeLayer(LAYER);if(map.getSource(SOURCE))map.removeSource(SOURCE);throw e;}
}
if(typeof module!=='undefined'&&module.exports)module.exports={setGrid,tile,SOURCE,LAYER,MODES,ROOT};else window.NordlPublicGrid={setGrid,SOURCE,LAYER};
})();