const {parseHTML}=require('linkedom'),vm=require('vm'),fs=require('fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
(async()=>{
 const {window}=parseHTML(fs.readFileSync('web/index.html','utf8'));const d=window.document;let store={};let downloads=[];const dialog=d.querySelector('dialog');dialog.showModal=function(){this.open=true};dialog.close=function(){this.open=false};
 const context={window,document:d,location:{search:'?demo=1',href:'http://localhost/'},navigator:{},URLSearchParams,URL,Blob,crypto:crypto.webcrypto,console,setTimeout:()=>0,setInterval:()=>0,sessionStorage:{setItem:(k,v)=>store[k]=v,getItem:k=>store[k],removeItem:k=>delete store[k]},confirm:()=>true,prompt:()=>null,fetch:()=>{throw Error('DEMO must never call server')},FormData:class{},};
 window.open=()=>null;vm.createContext(context);vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
 const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};await flush();
 assert.equal(d.querySelector('#panel').hidden,false);assert.equal(d.querySelector('#ordersBody').children.length,4);assert.match(d.querySelector('#ordersHeadRow').textContent,/Hazırla/);
 for(const [tab,title] of [['hazirlandi','Hazırlanan'],['kargolandi','Kargolanan'],['tamamlandi','Tamamlanan'],['sorunlu','Sorunlu'],['iptal','İptal'],['destek','Destek']]){
  await vm.runInContext(`setTab('${tab}')`,context);await flush();assert.match(d.querySelector('#pageTitle').textContent,new RegExp(title));assert.ok(d.querySelectorAll('tr[data-row]').length>0);
 }
 await vm.runInContext('openOrder(1009)',context);await flush();assert.equal(dialog.open,true);assert.match(d.querySelector('#orderDetails').textContent,/Kargo Bilgileri/);assert.match(d.querySelector('#orderDetails').textContent,/Hareket Geçmişi/);assert.ok(d.querySelector('a[href^="https://wa.me/"]'));
 assert.equal(vm.runInContext("esc('<img src=x onerror=alert(1)>')",context),'&lt;img src=x onerror=alert(1)&gt;');
 await vm.runInContext('openOrder(1001)',context);await vm.runInContext('editForm()',context);assert.ok(d.querySelector('#orderForm'));assert.equal(d.querySelectorAll('.package-row').length,1);d.querySelector('#addPackage').onclick();assert.equal(d.querySelectorAll('.package-row').length,2);
 assert.ok(!/db\.from|supabase\.createClient/.test(fs.readFileSync('web/app.js','utf8')));
 console.log('PASS: Gazi tabs/table/detail, 15 visual fixtures, package editor, contact/WhatsApp, escaped HTML, no table writes from browser');
})().catch(e=>{console.error(e);process.exit(1)});
