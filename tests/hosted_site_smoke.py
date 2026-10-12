import getpass,json,urllib.request
runtime=getpass.getpass('Runtime key: ');bypass=getpass.getpass('Site access token: ')
base='https://gazi-plpgsql-panel.brainyfrog33.chatgpt.site'
headers={'OAI-Sites-Authorization':'Bearer '+bypass,'x-gazi-runtime-key':runtime}
for path in ('/','/app.js','/api/me'):
 r=urllib.request.Request(base+path,headers=headers)
 with urllib.request.urlopen(r,timeout=60) as response:
  raw=response.read();assert response.status==200
  if path=='/api/me':assert json.loads(raw)['role']=='admin'
  if path=='/':assert 'Sipariş Sistemi'.encode() in raw
  print('PASS:',path,flush=True)

r=urllib.request.Request(base+'/api/rpc',data=json.dumps({'operation':'report','data':{'tab':'all'}}).encode(),headers={**headers,'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(r,timeout=60) as response:
 data=json.load(response);assert data['total']==15;assert data['amount']==16500
 print('PASS: /api/rpc report (15 orders, 16500 TL)',flush=True)
