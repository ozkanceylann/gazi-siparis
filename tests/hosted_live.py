"""Isolated hosted TEST backend verification; key enters through hidden stdin."""
import json,urllib.request,getpass,time
key=getpass.getpass('Runtime test key: ')
url='https://jarsxtpqzqzhlshpmgot.supabase.co/functions/v1/gazi-ops-runtime'
def req(path,data=None):
 r=urllib.request.Request(url,data=json.dumps({'path':path,'data':data or {}}).encode(),headers={'Content-Type':'application/json','x-gazi-runtime-key':key},method='POST')
 with urllib.request.urlopen(r,timeout=60) as x:return json.load(x)
def rpc(op,data=None):return req('rpc',{'operation':op,'data':data or {}})
def wait(jid):
 for _ in range(10):
  req('worker');j=req('jobs/'+str(jid))
  if j['state']=='done':return
  if j['last_error']:raise RuntimeError(j['last_error'])
  time.sleep(.3)
 raise RuntimeError('Job timeout')
u=req('me');assert u['role']=='admin'
initial=rpc('summary');assert initial['total']==15
orders=rpc('list',{'tab':'bekleyen'});o=orders['rows'][0];oid=o['siparis_no']
rpc('prepare',{'id':oid,'version':o['version']});req('worker');assert rpc('detail',{'id':oid})['order']['kargo_durumu']=='Hazırlandı'
j=rpc('cargo',{'id':oid});wait(j['job_id']);d=rpc('detail',{'id':oid});assert d['order']['kargo_durumu']=='Kargolandı';assert d['order']['environment']=='mock';assert len(rpc('label',{'id':oid})['barcodes'])==o['kargo_adet']
j=rpc('track',{'id':oid});wait(j['job_id']);d=rpc('detail',{'id':oid});assert d['order']['kargo_referans']
j=rpc('cancel',{'id':oid,'version':d['order']['version'],'reason':'Hosted test doğrulaması'});wait(j['job_id']);d=rpc('detail',{'id':oid});assert d['order']['kargo_durumu']=='İptal'
rpc('restore',{'id':oid,'version':d['order']['version']});d=rpc('detail',{'id':oid});assert d['order']['kargo_durumu']=='Bekliyor';assert d['order']['cargo_attempt']==2
report=rpc('report',{'tab':'all'});assert report['total']==15;assert report['amount']==16500
print('PASS: hosted PostgreSQL me/list/prepare/cargo/label/track/cancel/restore/report; 15 orders, total 16500 TL. No real DHL calls.')
