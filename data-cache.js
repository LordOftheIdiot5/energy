(()=>{'use strict';const promises=new Map();
function json(path){const key=new URL(path,location.href).href;if(!promises.has(key))promises.set(key,fetch(key,{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status+' '+path);return r.json();}).catch(e=>{promises.delete(key);throw e;}));return promises.get(key);}
function response(path){return json(path).then(data=>({ok:true,json:()=>Promise.resolve(data)}));}
function when(ids,callback){let started=false;const run=()=>{if(started)return;if(ids.some(id=>{const p=document.getElementById(id);return p&&!p.hidden&&p.getClientRects().length;})){started=true;callback();}};window.addEventListener('hashchange',()=>requestAnimationFrame(run));requestAnimationFrame(run);}
function day(){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Oslo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
function comparable(z){return !z.stale&&z.zone!=='GB'&&z.marketType!=='market_index'&&(z.today?z.today.date===day()&&z.today.complete===true&&z.today.eur?.length>0&&z.today.eur.every(Number.isFinite):z.date===day()&&z.complete===true&&z.cents?.length>0&&z.cents.every(Number.isFinite));}
window.NordlData={json,fetch:response,when,day,comparable};
})();