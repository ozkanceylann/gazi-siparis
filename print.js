'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const printButton=document.querySelector('#print');printButton.onclick=()=>window.print();
try{
 if(new URLSearchParams(location.search).has('waiting')){document.querySelector('#notice').textContent='Kargo işlemi sürüyor…';printButton.hidden=true;}
 else{
  const data=JSON.parse(sessionStorage.getItem('gazi-print')||'null');sessionStorage.removeItem('gazi-print');
  if(!data)throw Error('Yazdırılacak sipariş bulunamadı. Panelden etiketi yeniden açın.');
  const o=data.order,l=data.label,type=data.type;document.title='Gazi · #'+o.siparis_no;
  if(type==='cargo'&&l.pdf_base64){
   if(!l.pdf_base64.startsWith('JVBER'))throw Error('Geçerli PDF etiketi bulunamadı');
   const url=URL.createObjectURL(new Blob([Uint8Array.from(atob(l.pdf_base64),c=>c.charCodeAt(0))],{type:'application/pdf'}));location.replace(url);
  }else{
   const packages=type==='adisyon'?[{}]:o.packages;
   const official=type==='cargo'&&o.environment!=='mock';
   if(official){printButton.hidden=true;document.querySelector('#notice').textContent='Resmî DHL ZPL etiketi hazır. ZPL yazıcıda kullanmak için indirin. PDF yazdırma için sunucuda Labelary dönüşümünü etkinleştirin. Aşağıdaki özet taşıyıcı etiketi yerine kullanılamaz.';}
   document.querySelector('#labels').innerHTML=packages.map((p,i)=>`<section class="label ${type==='preparation'?'preparation':''}">${o.environment==='mock'?'<p class="test">TEST · GERÇEK KARGO DEĞİL</p>':''}<h2>${type==='preparation'?'HAZIRLAMA ETİKETİ':type==='adisyon'?'SİPARİŞ ADİSYONU':'KARGO ÖZETİ'} · #${o.siparis_no}</h2><b>${esc(o.ad_soyad)}</b><p>${esc(o.musteri_tel)}</p><p>${esc(o.adres)}<br>${esc(o.sehir)} / ${esc(o.ilce)}</p><p>${esc(o.urun_bilgisi)}</p>${type!=='adisyon'?`<p>Paket ${i+1} / ${packages.length} · ${esc(p.kg)} KG / ${esc(p.desi)} desi</p>`:''}<p>${Number(o.toplam_tutar).toLocaleString('tr-TR')} TL · ${esc(o.odeme_sekli)}</p>${o.notlar?`<p>Not: ${esc(o.notlar)}</p>`:''}${l?.barcodes?.[i]?`<svg class="barcode" data-value="${esc(l.barcodes[i].barcode)}"></svg>`:''}${type==='cargo'?`<p>Takip: ${esc(o.kargo_takip_kodu)}<br>Referans: ${esc(o.kargo_referans)}</p>`:''}</section>`).join('');
   document.querySelectorAll('.barcode').forEach(s=>JsBarcode(s,s.dataset.value,{format:'CODE128',width:2,height:60,fontSize:12}));
   if(l?.zpl){const b=document.querySelector('#zpl');b.hidden=false;b.onclick=()=>{const u=URL.createObjectURL(new Blob([l.zpl],{type:'text/plain'}));const a=document.createElement('a');a.href=u;a.download='GAZI-'+o.siparis_no+'.zpl';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};}
  }
 }
}catch(e){document.querySelector('#notice').textContent=e.message;printButton.hidden=true;}
