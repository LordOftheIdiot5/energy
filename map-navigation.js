(()=>{'use strict';
const states=new WeakMap();
function clamp(v,b){const [x,y,w,h]=v,[bx,by,bw,bh]=b;return [Math.max(bx,Math.min(bx+bw-w,x)),Math.max(by,Math.min(by+bh-h,y)),w,h];}
function zoomed(v,b,f){const w=Math.max(b[2]/8,Math.min(b[2],v[2]*f)),h=w*b[3]/b[2];return clamp([v[0]+(v[2]-w)/2,v[1]+(v[3]-h)/2,w,h],b);}
function apply(root,state,v){state.view=clamp(v,state.base);root.setAttribute('viewBox',state.view.join(' '));}
function setup(root,state){let drag=null,suppress=false;
root.addEventListener('pointerdown',e=>{if(e.button!==0||!e.isPrimary)return;suppress=false;const matrix=root.getScreenCTM();if(!matrix)return;let inv;try{inv=matrix.inverse();}catch{return;}drag={id:e.pointerId,x:e.clientX,y:e.clientY,view:[...state.view],inv,active:false};});
root.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(!drag.active&&Math.hypot(dx,dy)<6)return;if(!drag.active){drag.active=true;root.setPointerCapture(e.pointerId);root.classList.add('map-dragging');}const a=new DOMPoint(0,0).matrixTransform(drag.inv),b=new DOMPoint(dx,dy).matrixTransform(drag.inv);apply(root,state,[drag.view[0]-(b.x-a.x),drag.view[1]-(b.y-a.y),drag.view[2],drag.view[3]]);});
function end(e){if(!drag||e.pointerId!==drag.id)return;suppress=drag.active;drag=null;root.classList.remove('map-dragging');}
for(const k of ['pointerup','pointercancel','lostpointercapture'])root.addEventListener(k,end);
root.addEventListener('click',e=>{if(suppress){e.preventDefault();e.stopImmediatePropagation();suppress=false;}},true);
root.addEventListener('keydown',e=>{if(e.target!==root)return;const v=state.view,k=e.key;let n;if(k==='+'||k==='=')n=zoomed(v,state.base,.75);else if(k==='-')n=zoomed(v,state.base,1/.75);else if(k==='Home')n=state.base;else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(k)){n=[...v];n[0]+=(k==='ArrowLeft'?-1:k==='ArrowRight'?1:0)*v[2]*.12;n[1]+=(k==='ArrowUp'?-1:k==='ArrowDown'?1:0)*v[3]*.12;}else return;e.preventDefault();apply(root,state,n);});}
function base(root,b,key){let state=states.get(root);if(!state){state={base:[...b],view:[...b],key};states.set(root,state);setup(root,state);}else if(key!==state.key||b.some((v,i)=>v!==state.base[i])){state.base=[...b];state.view=[...b];state.key=key;}apply(root,state,state.view);}
document.querySelectorAll('[data-map][data-action]').forEach(button=>button.addEventListener('click',()=>{const root=document.getElementById(button.dataset.map),state=states.get(root);if(state)apply(root,state,button.dataset.action==='reset'?state.base:zoomed(state.view,state.base,button.dataset.action==='in'?.75:1/.75));}));
window.NordlMap={base};
})();