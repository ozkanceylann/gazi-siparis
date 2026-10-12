"""DHL sandbox and HTTPS gateway transport; business rules live in PostgreSQL."""
import os,json,base64,urllib.request,urllib.error
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
class CarrierError(RuntimeError):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None

def http(url,method='GET',body=None,headers=None):
 if not url.startswith('https://'):raise CarrierError('Servis adresi HTTPS olmalı')
 req=urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False,default=str).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})},method=method)
 try:
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as r:
   raw=r.read(8_000_001)
   if len(raw)>8_000_000:raise CarrierError('Kargo yanıtı çok büyük')
   return r.status,json.loads(raw)
 except urllib.error.HTTPError as e:return e.code,{}
 except (urllib.error.URLError,TimeoutError,ValueError):raise CarrierError('Kargo servisi yanıt vermedi')
def first(v):return v[0] if isinstance(v,list) and v else v

def stamp(value):
 if not value:return None
 v=str(value)
 for fmt in ('%d.%m.%Y %H:%M:%S','%d.%m.%Y %H:%M'):
  try:return datetime.strptime(v,fmt).replace(tzinfo=timezone(timedelta(hours=3))).isoformat()
  except ValueError:pass
 try:
  d=datetime.fromisoformat(v.replace('Z','+00:00'))
  return (d if d.tzinfo else d.replace(tzinfo=timezone(timedelta(hours=3)))).isoformat()
 except ValueError:return None

def mock(job,o,s,l):
 now=datetime.now(timezone.utc).isoformat();ref=s['reference'] if s else f"GZTEST-{o['siparis_no']}-{o['cargo_attempt']}"
 if job['kind']=='cancel':return {'cancelled':True}
 r={'reference':ref,'tracking':s['tracking'] if s else f"TEST{o['siparis_no']:09d}{o['cargo_attempt']}",'environment':'mock','status_code':s['status_code'] if s else 1,'state':s['state'] if s else 'TEST · Gönderi hazırlandı','state_at':s['state_at'].isoformat() if s and s['state_at'] else now,'branch':s['branch'] if s else 'TEST Şubesi','branch_phone':s['branch_phone'] if s else '', 'events':[{'id':'mock-created','title':'TEST · Simülasyon kaydı','at':now}]}
 if job['kind'] in ('create','label'):
  bs=[{'barcode':ref+'-'+str(i+1),'pieceNumber':i+1} for i in range(len(o['packages']))]
  r['label']={'zpl':'\n'.join('^XA^FO20,20^FDTEST - GERCEK KARGO DEGIL^FS^FO20,80^BCN,80,Y,N,N^FD'+b['barcode']+'^FS^XZ' for b in bs),'barcodes':bs}
 return r

def dhl_payload(o,ref):
 cod='kapıda' in o['odeme_sekli'].lower() or 'kapida' in o['odeme_sekli'].lower()
 return {'order':{'referenceId':ref,'barcode':ref,'billOfLandingId':'GAZI TEST','isCOD':int(cod),'codAmount':float(o['toplam_tutar']) if cod else 0,'shipmentServiceType':1,'marketPlaceShortCode':'','marketPlaceSaleCode':'','packagingType':3,'content':o['urun_bilgisi'],'smsPreference1':0,'smsPreference2':0,'smsPreference3':0,'paymentType':1,'deliveryType':1,'description':o['urun_bilgisi']},'orderPieceList':[{'barcode':ref+'-'+str(i+1),'kg':float(p['kg']),'desi':float(p['desi']),'content':o['urun_bilgisi']} for i,p in enumerate(o['packages'])],'shipper':{'customerId':os.environ['DHL_CUSTOMER_NUMBER'],'refCustomerId':'','cityCode':0,'districtCode':0,'cityName':'','districtName':'','address':'','bussinessPhoneNumber':'','taxOffice':'','taxNumber':'','fullName':'','homePhoneNumber':'','mobilePhoneNumber':''},'recipient':{'cityCode':o['sehir_kodu'] or 0,'districtCode':o['ilce_kodu'] or 0,'cityName':o['sehir'],'districtName':o['ilce'],'address':o['adres'],'fullName':o['ad_soyad'],'mobilePhoneNumber':o['musteri_tel'].removeprefix('90')}}

def sandbox(job,o,s,l):
 for k in ('DHL_CLIENT_ID','DHL_CLIENT_SECRET','DHL_CUSTOMER_NUMBER','DHL_PASSWORD'):
  if not os.environ.get(k):raise CarrierError('DHL sandbox bağlantı bilgileri eksik')
 base='https://testapi.mngkargo.com.tr/mngapi/api/'
 h={'Accept':'application/json','x-api-version':'v1','X-IBM-Client-Id':os.environ['DHL_CLIENT_ID'],'X-IBM-Client-Secret':os.environ['DHL_CLIENT_SECRET']}
 status,a=http(base+'token','POST',{'customerNumber':os.environ['DHL_CUSTOMER_NUMBER'],'password':os.environ['DHL_PASSWORD'],'identityType':1},h)
 if status!=200 or not a.get('jwt'):raise CarrierError('DHL sandbox kimlik doğrulaması başarısız')
 h['Authorization']='Bearer '+a['jwt'];ref=s['reference'] if s else f"GZTEST-{o['siparis_no']}-{o['cargo_attempt']}"
 def call(path,method='GET',body=None):return http(base+path,method,body,h)
 if job['kind']=='cancel':
  status,_=call('barcodecmdapi/cancelshipment','PUT',{'referenceId':ref,'shipmentId':s['tracking']})
  if status not in (200,204):raise CarrierError('DHL iptali doğrulanmadı (HTTP '+str(status)+')')
  return {'cancelled':True}
 if job['kind'] in ('create','label'):
  if s and l and (l['pdf_base64'] or l['zpl']):return {'reference':ref,'tracking':s['tracking'],'environment':'sandbox','status_code':s['status_code'],'state':s['state'],'state_at':s['state_at'].isoformat(),'label':{k:l[k] for k in ('zpl','pdf_base64','barcodes')}}
  status,existing=call('standardqueryapi/getorder/'+quote(ref,safe=''))
  if status==404:
   if job['kind']=='label':raise CarrierError('Mevcut kargo doğrulanamadı; yeni sipariş açılmadı')
   status,r=call('standardcmdapi/createOrder','POST',dhl_payload(o,ref))
   if status not in (200,201) or not first(r).get('orderInvoiceId'):raise CarrierError('DHL sipariş kaydı doğrulanmadı; şube/adres bilgisini kontrol edin (HTTP '+str(status)+')')
  elif status!=200:raise CarrierError('Mevcut gönderi sorgusu başarısız; çift kayıt oluşturmamak için durduruldu')
  p=dhl_payload(o,ref)
  status,bar=call('barcodecmdapi/createbarcode','POST',{'referenceId':ref,'billOfLandingId':'','isCOD':p['order']['isCOD'],'codAmount':p['order']['codAmount'],'printReferenceBarcodeOnError':0,'packagingType':3,'orderPieceList':p['orderPieceList']})
  if status not in (200,201) or not first(bar).get('shipmentId'):raise CarrierError('DHL barkod işlemi doğrulanmadı; aynı referans ile yeniden deneyin')
  records=bar if isinstance(bar,list) else [bar];bs=sorted([b for r in records for b in r.get('barcodes',[])],key=lambda b:b['pieceNumber'])
  if len(bs)!=len(o['packages']) or len({b['barcode'] for b in bs})!=len(bs) or any(not b.get('value','').startswith('^XA') for b in bs):raise CarrierError('DHL paket barkodları doğrulanmadı')
  zpl='\n'.join(b['value'] for b in bs);label={'zpl':zpl,'barcodes':[{'pieceNumber':b['pieceNumber'],'barcode':str(b['barcode'])} for b in bs]}
  if os.environ.get('LABELARY_ENABLED')=='true':
   req=urllib.request.Request('https://api.labelary.com/v1/printers/8dpmm/labels/4.1x4.8/',data=zpl.encode(),headers={'Accept':'application/pdf','Content-Type':'application/x-www-form-urlencoded'},method='POST')
   try:
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=25) as response:
     raw=response.read(8_000_001)
     if raw.startswith(b'%PDF') and len(raw)<=8_000_000:label['pdf_base64']=base64.b64encode(raw).decode()
   except (urllib.error.URLError,TimeoutError):pass
  return {'reference':ref,'tracking':str(first(bar)['shipmentId']),'environment':'sandbox','status_code':1,'state':'Gönderi hazırlandı','state_at':datetime.now(timezone.utc).isoformat(),'label':label,'events':[]}
 status,state=call('standardqueryapi/getshipmentstatus/'+quote(ref,safe=''))
 if status!=200:raise CarrierError('DHL durum sorgusu başarısız (HTTP '+str(status)+')')
 state=first(state);mstatus,mov=call('standardqueryapi/trackshipment/'+quote(ref,safe=''));events=[]
 if mstatus==200 and isinstance(mov,list):
  for m in mov:
   at=stamp(m.get('eventDateTime2') or m.get('eventDateTime'))
   if at:events.append({'id':str(m['eventSequence']),'title':str(m.get('eventStatus') or m.get('description') or 'Kargo hareketi'),'at':at,'branch':m.get('locationAddress') or m.get('location'),'branch_phone':m.get('locationPhone')})
 events.sort(key=lambda e:datetime.fromisoformat(e['at']));latest=events[-1] if events else {};code=int(state['shipmentStatusCode'])
 if code not in range(1,9):raise CarrierError('DHL bilinmeyen durum kodu döndürdü')
 return {'reference':str(state.get('referenceId') or ref),'tracking':str(state.get('shipmentId') or s['tracking']),'environment':'sandbox','status_code':code,'state':str(state.get('shipmentStatus') or ''),'state_at':stamp(state.get('deliveryDate') or state.get('shipmentStatusDate')) or latest.get('at') or datetime.now(timezone.utc).isoformat(),'events':events,'branch':latest.get('branch'),'branch_phone':latest.get('branch_phone'),'movement_error':None if mstatus==200 else 'Hareket servisi yanıt vermedi'}

def process(job,o,s,l):
 if job['kind']=='codes':
  from app.db import connect
  with connect() as c:r=c.execute('SELECT c.code AS city_code,d.code AS district_code FROM cities c JOIN districts d ON d.city_code=c.code WHERE lower(c.name)=lower(%s) AND lower(d.name)=lower(%s)',(o['sehir'],o['ilce'])).fetchone()
  if not r:raise CarrierError('İl/ilçe listesi bulunamadı; doğrulanmış DHL kodlarını içe aktarın')
  return r
 if job['kind']=='reaction':
  url=os.environ.get('WHATSAPP_REACTION_URL','')
  if not url:return {'skipped':True}
  status,_=http(url,'POST',{'siparis_no':o['source_order_no'] or o['siparis_no'],'emoji':job['payload']['emoji']},{'Authorization':'Bearer '+os.environ.get('WHATSAPP_REACTION_TOKEN','')})
  if status not in (200,201,204):raise CarrierError('WhatsApp tepkisi gönderilemedi')
  return {'ok':True}
 mode=os.environ.get('CARRIER_MODE','mock')
 if s and s['environment']!=mode:raise CarrierError('Gönderi ile worker ortamı farklı')
 if mode=='mock':return mock(job,o,s,l)
 if mode=='sandbox' and not os.environ.get('CARRIER_GATEWAY_URL'):return sandbox(job,o,s,l)
 if mode not in ('sandbox','live'):raise CarrierError('Kargo çalışma modu geçersiz')
 if mode=='live' and os.environ.get('LIVE_CARGO_ENABLED')!='true':raise CarrierError('Canlı kargo etkin değil')
 url=os.environ.get('CARRIER_GATEWAY_URL','');token=os.environ.get('CARRIER_GATEWAY_TOKEN','')
 if not url or not token:raise CarrierError('HTTPS kargo gateway yapılandırılmalı')
 ref=s['reference'] if s else f"GAZI-{o['siparis_no']}-{o['cargo_attempt']}"
 status,r=http(url,'POST',{'operation':job['kind'],'reference':ref,'idempotency_key':ref,'order':o,'shipment':s,'payload':job['payload']},{'Authorization':'Bearer '+token})
 if status!=200:raise CarrierError('Kargo gateway işlemi başarısız')
 if job['kind']!='cancel' and (r.get('environment')!=mode or not r.get('reference') or int(r.get('status_code',0)) not in range(1,9) or not stamp(r.get('state_at'))):raise CarrierError('Kargo gateway sözleşmesi doğrulanmadı')
 return r

def check_connection():
 mode=os.environ.get('CARRIER_MODE','mock')
 if mode=='mock':return {'mode':mode,'message':'TEST / SİMÜLASYON · Gerçek DHL çağrısı yapılmaz'}
 if mode=='sandbox' and not os.environ.get('CARRIER_GATEWAY_URL'):
  if any(not os.environ.get(k) for k in ('DHL_CLIENT_ID','DHL_CLIENT_SECRET','DHL_CUSTOMER_NUMBER','DHL_PASSWORD')):raise CarrierError('DHL sandbox bilgileri eksik')
  status,result=http('https://testapi.mngkargo.com.tr/mngapi/api/token','POST',{'customerNumber':os.environ['DHL_CUSTOMER_NUMBER'],'password':os.environ['DHL_PASSWORD'],'identityType':1},{'X-IBM-Client-Id':os.environ['DHL_CLIENT_ID'],'X-IBM-Client-Secret':os.environ['DHL_CLIENT_SECRET'],'x-api-version':'v1'})
  if status!=200 or not result.get('jwt'):raise CarrierError('DHL sandbox bağlantısı doğrulanamadı')
  return {'mode':mode,'message':'DHL sandbox bağlantısı doğrulandı'}
 if not os.environ.get('CARRIER_GATEWAY_URL') or not os.environ.get('CARRIER_GATEWAY_TOKEN'):raise CarrierError('Kargo gateway bilgileri eksik')
 return {'mode':mode,'message':'HTTPS gateway yapılandırıldı; servis erişimi ilk işlemde doğrulanacak'}
