import getpass,json,urllib.request
key=getpass.getpass('Runtime key: ');url='https://jarsxtpqzqzhlshpmgot.supabase.co/functions/v1/gazi-live-runtime'
def req(path,data=None):
 r=urllib.request.Request(url,data=json.dumps({'path':path,'data':data or {}}).encode(),headers={'Content-Type':'application/json','x-gazi-runtime-key':key},method='POST')
 with urllib.request.urlopen(r,timeout=60) as x:return json.load(x)
print('me',req('me')['mode'],flush=True)
print('summary',req('rpc',{'operation':'summary','data':{}}),flush=True)
print('connection',req('carrier/status')['message'],flush=True)
j=req('rpc',{'operation':'track','data':{'id':9436}})
for _ in range(10):
 req('worker');state=req('jobs/'+str(j['job_id']))
 if state['state']=='done':break
 if state.get('last_error'):raise RuntimeError(state['last_error'])
else:raise RuntimeError('Tracking job not finished')
d=req('rpc',{'operation':'detail','data':{'id':9436}});assert d['order']['environment']=='live';print('PASS: LIVE carrier tracking persisted with movement history',len(d['events']),flush=True)
