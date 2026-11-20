import {probe,recover} from "./worker.mjs";
const now=Date.parse("2026-11-20T12:00:00Z");
export default {async fetch(req) {
 const path=new URL(req.url).pathname,trace=[];
 const mocked=async(url,init)=>{
   // This runs inside the actual workerd runtime, exercising Request options.
   new Request(url,init);
   trace.push({redirect:init.redirect,hasCache:!!init.cache,hasCf:!!init.cf,method:init.method||"GET"});
   if(path==="/redirect")return new Response(null,{status:302,headers:{Location:"https://example.invalid/never-follow"}});
   if(url.includes("/runs?"))return Response.json({total_count:0});
   if(url.endsWith("/dispatches"))return new Response(null,{status:204});
   return Response.json({generated:new Date(now-60000).toISOString(),zones:[{}],europe:[]});
 };
 try {
   if(path==="/probe"||path==="/redirect")return Response.json({age:await probe(mocked,now),trace});
   if(path==="/recover")return Response.json({action:await recover({GITHUB_DISPATCH_TOKEN:"TESTONLY"},mocked),trace});
   return new Response("Not found",{status:404});
 }catch(e){return Response.json({error:e.code||e.name,trace});}
}};
