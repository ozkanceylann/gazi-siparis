import getpass,json,urllib.request
runtime=getpass.getpass('Runtime key: ');bypass=getpass.getpass('Site access token: ')
base='https://gazi-plpgsql-panel.brainyfrog33.chatgpt.site'
headers={'OAI-Sites-Authorization':'Bearer '+bypass,'x-gazi-runtime-key':runtime}
for path in ('/','/app.js','/api/me'):
 r=urllib.request.Request(base+path,headers=headers)
 with urllib.request.urlopen(r,timeout=60) as response:
  raw=response.read();assert response.status==200
  if path=='/api/me':assert json.loads(raw)['role']=='admin';assert json.loads(raw)['mode']=='live';assert json.loads(raw)['shipping_enabled'] is False
  if path=='/':assert 'Sipariş Sistemi'.encode() in raw
  print('PASS:',path,flush=True)

r=urllib.request.Request(base+'/api/rpc',data=json.dumps({'operation':'report','data':{'tab':'all'}}).encode(),headers={**headers,'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(r,timeout=60) as response:
 data=json.load(response);assert data['total']==2480;assert data['amount']==4415999
 print('PASS: /api/rpc report (2480 real orders, 4415999 TL)',flush=True)
