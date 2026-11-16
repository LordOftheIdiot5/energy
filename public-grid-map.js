(()=>{'use strict';
const SOURCE='nve-published-grid',LAYER='nve-published-grid-overlay';
const ROOT='https://kart.nve.no/enterprise/rest/services/Nettanlegg5/MapServer';
const OVERVIEW_SOURCE='nve-grid-national-overview',OVERVIEW_LAYER='nve-grid-national-image';
const MIN_ZOOM={transmission:5,cables:6,regional:8,stations:9,all:6};
const MODES=Object.freeze({transmission:'0',regional:'1',cables:'2',stations:'4',all:'0,1,2,4'});
function tile(mode){
 if(!Object.hasOwn(MODES,mode))throw Error('Unknown public grid layer');
 return ROOT+'/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&layers=show:'+MODES[mode]+'&f=image';
}
function overview(mode){
 if(!['transmission','cables','all'].includes(mode))return null;
 const west=3,south=55,east=33,north=73,R=6378137,rad=Math.PI/180;
 const mx=x=>R*x*rad,my=y=>R*Math.log(Math.tan(Math.PI/4+y*rad/2));
 const bbox=[mx(west),my(south),mx(east),my(north)],height=mode==='transmission'?2048:4096,width=Math.round(height*(bbox[2]-bbox[0])/(bbox[3]-bbox[1]));
 const layers=mode==='all'?'0,2':MODES[mode];
 // Source-rendered national image at the service's supported display scale,
 // then ordinary raster downsampling for the continent view. No hidden
 // layers, geometry extraction or modified source scale limits.
 const url=ROOT+'/export?bbox='+bbox.join(',')+'&bboxSR=3857&imageSR=3857&size='+width+','+height+'&format=png32&transparent=true&layers=show:'+layers+'&f=image';
 return {type:'image',url,coordinates:[[west,north],[east,north],[east,south],[west,south]]};
}
function setGrid(map,mode){
 if(mode!=='off'&&!Object.hasOwn(MODES,mode))throw Error('Unknown public grid layer');
 if(map.getLayer(LAYER))map.removeLayer(LAYER);
 if(map.getLayer(OVERVIEW_LAYER))map.removeLayer(OVERVIEW_LAYER);
 if(map.getSource(SOURCE))map.removeSource(SOURCE);
 if(map.getSource(OVERVIEW_SOURCE))map.removeSource(OVERVIEW_SOURCE);
 if(mode==='off')return false;
 const before=map.getLayer('energy-flows')?'energy-flows':undefined;
 try{const image=overview(mode),threshold=MIN_ZOOM[mode];if(image){map.addSource(OVERVIEW_SOURCE,image);map.addLayer({id:OVERVIEW_LAYER,type:'raster',source:OVERVIEW_SOURCE,maxzoom:threshold,paint:{'raster-opacity':.95,'raster-fade-duration':0}},before);}map.addSource(SOURCE,{type:'raster',tiles:[tile(mode)],tileSize:256,minzoom:4,maxzoom:11,bounds:[3,55,33,73],attribution:'<a href="https://kart.nve.no/enterprise/rest/services/Nettanlegg5/MapServer">NVE · Nettanlegg utbygd</a> / <a href="https://data.norge.no/nlod/en/1.0">NLOD 1.0</a>'});
 map.addLayer({id:LAYER,type:'raster',source:SOURCE,minzoom:threshold,paint:{'raster-opacity':.9,'raster-fade-duration':0}},before);return true;}
 catch(e){for(const id of [LAYER,OVERVIEW_LAYER])if(map.getLayer(id))map.removeLayer(id);for(const id of [SOURCE,OVERVIEW_SOURCE])if(map.getSource(id))map.removeSource(id);throw e;}
}
if(typeof module!=='undefined'&&module.exports)module.exports={setGrid,tile,SOURCE,LAYER,MODES,ROOT,MIN_ZOOM,overview,OVERVIEW_SOURCE,OVERVIEW_LAYER};else window.NordlPublicGrid={setGrid,SOURCE,LAYER,MIN_ZOOM,OVERVIEW_SOURCE,OVERVIEW_LAYER};
})();