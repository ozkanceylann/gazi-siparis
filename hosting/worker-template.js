const assets=__ASSETS__;
const JSON_HEADERS={'Content-Type':'application/json','Cache-Control':'no-store'};
function json(v,status=200){return new Response(JSON.stringify(v),{status,headers:JSON_HEADERS});}
async function csrf(key,id){const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);const sig=await crypto.subtle.sign('HMAC',k,new TextEncoder().encode(id));return [...new Uint8Array(sig)].map(x=>x.toString(16).padStart(2,'0')).join('');}
export default {async fetch(request,env,ctx){const url=new URL(request.url);if(url.pathname.startsWith('/api/')){
 if(!env.GAZI_RUNTIME_KEY||!env.GAZI_EDGE_URL)return json({detail:'Sunucu bağlantısı hazır değil'},503);
 const identity=request.headers.get('oai-authenticated-user-id');const service=request.headers.get('x-gazi-runtime-key')===env.GAZI_RUNTIME_KEY;
 if(!identity&&!service)return json({detail:'ChatGPT hesabınızla giriş yapın'},401);
 const token=await csrf(env.GAZI_RUNTIME_KEY,identity||'service');
 if(request.method==='POST'&&!service&&(request.headers.get('origin')!==url.origin||request.headers.get('X-CSRF-Token')!==token))return json({detail:'İstek kaynağı doğrulanamadı'},403);
 if(!['GET','POST'].includes(request.method))return json({detail:'Geçersiz istek'},405);
 const path=url.pathname.slice(5);if(!['me','rpc','carrier/status','logout','worker'].includes(path)&&!/^jobs\/\d+$/.test(path))return json({detail:'Yol bulunamadı'},404);
 try{const body=request.method==='POST'?await request.json():{};const upstream=await fetch(env.GAZI_EDGE_URL,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json','x-gazi-runtime-key':env.GAZI_RUNTIME_KEY},body:JSON.stringify({path,data:body}),signal:AbortSignal.timeout(55000)});const v=await upstream.json();if(path==='me'&&upstream.ok)v.csrf=token;return json(v,upstream.status);}catch{return json({detail:'Veritabanı bağlantısı yanıt vermedi'},503);}
 }
 const name=url.pathname==='/'?'index.html':url.pathname.slice(1);const a=assets[name];if(!a)return new Response('Not found',{status:404});const bytes=Uint8Array.from(atob(a.content),c=>c.charCodeAt(0));return new Response(bytes,{headers:{'Content-Type':a.type,'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Cache-Control':'no-cache','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-src 'self' blob:; connect-src 'self'; base-uri 'self'; form-action 'self'"}});
}};
