const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
const source=fs.readFileSync('hosting/worker-template.js','utf8').replace('__ASSETS__','{}');const mod=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));const worker=mod.default;
const env={GAZI_RUNTIME_KEY:'TEST-RUNTIME-KEY',GAZI_EDGE_URL:'https://test.invalid'};let upstream=0;const realFetch=global.fetch;
global.fetch=async()=>{upstream++;return new Response(JSON.stringify({id:1,name:'Test','role':'admin'}),{headers:{'Content-Type':'application/json'}})};
assert.equal((await worker.fetch(new Request('https://site.test/api/me'),env,{})).status,401);
const me=await worker.fetch(new Request('https://site.test/api/me',{headers:{'oai-authenticated-user-id':'owner'}}),env,{});const u=await me.json();assert.ok(u.csrf);
const wrong=await worker.fetch(new Request('https://site.test/api/rpc',{method:'POST',headers:{'oai-authenticated-user-id':'owner',origin:'https://site.test','X-CSRF-Token':'bad'},body:'{}'}),env,{});assert.equal(wrong.status,403);
const ok=await worker.fetch(new Request('https://site.test/api/rpc',{method:'POST',headers:{'oai-authenticated-user-id':'owner',origin:'https://site.test','X-CSRF-Token':u.csrf},body:'{"operation":"list"}'}),env,{});assert.equal(ok.status,200);assert.equal(upstream,2);const fallback=await worker.fetch(new Request('https://site.test/api/me',{headers:{'oai-authenticated-user-email':'verified-owner@example.invalid'}}),env,{});assert.equal(fallback.status,200);global.fetch=realFetch;
console.log('PASS: hosted owner identity, CSRF, server-only proxy credentials');
})().catch(e=>{console.error(e);process.exit(1)});
