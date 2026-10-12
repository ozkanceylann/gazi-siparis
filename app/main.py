"""HTTP/session transport. Order decisions and writes live in PL/pgSQL."""
import os, secrets
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
import psycopg
from app.db import connect
from app.security import password_hash, verify_password, token_hash

app=FastAPI(title='Gazi Sipariş',docs_url=None,redoc_url=None,openapi_url=None)
WEB=Path(__file__).resolve().parent.parent/'web'
ORIGIN=os.environ.get('APP_ORIGIN','http://localhost:8000').rstrip('/')
DUMMY=password_hash(secrets.token_urlsafe(32))
OPERATIONS={'list','summary','report','detail','cities','districts','users','connection','create','edit','prepare','waiting','cargo','track','retry_label','codes','cancel','restore','hide','label','resolve','duplicates','merge','bulk_track'}

@app.middleware('http')
async def headers(request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS') and request.url.path!='/api/ingest' and request.headers.get('origin')!=ORIGIN:
        return JSONResponse({'detail':'İstek kaynağı doğrulanamadı'},403)
    if int(request.headers.get('content-length','0') or 0)>1_000_000:
        return JSONResponse({'detail':'İstek çok büyük'},413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(psycopg.Error)
async def sql_error(request, exc):
    msg=exc.diag.message_primary if exc.sqlstate=='P0001' else 'İşlem tamamlanamadı; alanları kontrol edin'
    return JSONResponse({'detail':msg},409)

def actor(request,c):
    u=c.execute('SELECT u.id,u.name,u.role,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>now() AND u.active',(token_hash(request.cookies.get('gazi_session','')),)).fetchone()
    if not u: raise HTTPException(401,'Oturum açın')
    if request.method!='GET' and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),u['csrf']):
        raise HTTPException(403,'Oturum doğrulanamadı')
    return u

class Login(BaseModel):
    phone:str=Field(max_length=25)
    password:str=Field(min_length=1,max_length=200)
class RPC(BaseModel):
    operation:str=Field(max_length=30)
    data:dict=Field(default_factory=dict)

@app.post('/api/login')
def login(data:Login):
    with connect() as c:
        phone=c.execute('SELECT phone(%s) AS phone',(data.phone,)).fetchone()['phone']
        r=c.execute("INSERT INTO login_attempts VALUES(%s,1,now()) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN login_attempts.window_start<now()-interval '15 minutes' THEN 1 ELSE login_attempts.count+1 END,window_start=CASE WHEN login_attempts.window_start<now()-interval '15 minutes' THEN now() ELSE login_attempts.window_start END RETURNING count",(phone,)).fetchone()
        c.commit()
        if r['count']>10: raise HTTPException(429,'15 dakika sonra yeniden deneyin')
        u=c.execute('SELECT * FROM users WHERE phone=%s AND active',(phone,)).fetchone()
        ok=verify_password(data.password,u['password_hash'] if u else DUMMY)
        if not u or not ok: raise HTTPException(401,'Telefon veya şifre hatalı')
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        c.execute("INSERT INTO sessions VALUES(%s,%s,%s,now()+interval '12 hours')",(token_hash(token),u['id'],csrf))
        c.execute('DELETE FROM login_attempts WHERE key=%s',(phone,))
        c.execute('DELETE FROM sessions WHERE expires_at<now()')
    response=JSONResponse({'id':u['id'],'name':u['name'],'role':u['role'],'csrf':csrf})
    response.set_cookie('gazi_session',token,httponly=True,secure=os.environ.get('COOKIE_SECURE','true')=='true',samesite='strict',max_age=43200)
    return response

@app.get('/api/me')
def me(request:Request):
    with connect() as c: return actor(request,c)

@app.post('/api/logout')
def logout(request:Request):
    with connect() as c:
        actor(request,c);c.execute('DELETE FROM sessions WHERE token_hash=%s',(token_hash(request.cookies.get('gazi_session','')),))
    r=JSONResponse({'ok':True});r.delete_cookie('gazi_session');return r

@app.post('/api/rpc')
def rpc(data:RPC,request:Request):
    if data.operation not in OPERATIONS: raise HTTPException(400,'Geçersiz işlem')
    with connect() as c:
        u=actor(request,c)
        result=c.execute('SELECT rpc(%s,%s,%s) AS result',(u['id'],data.operation,Jsonb(data.data))).fetchone()['result']
        return JSONResponse(jsonable_encoder(result))

@app.get('/api/jobs/{job_id}')
def job(job_id:int,request:Request):
    with connect() as c:
        u=actor(request,c)
        j=c.execute("SELECT j.id,j.kind,j.state,j.attempts,j.last_error,j.run_at FROM jobs j JOIN orders o ON o.siparis_no=j.order_id WHERE j.id=%s AND (%s OR o.seller_id=%s)",(job_id,u['role']=='admin',u['id'])).fetchone()
        if not j: raise HTTPException(404,'İşlem bulunamadı')
        return j

@app.post('/api/ingest')
def ingest(data:dict,request:Request):
    expected=os.environ.get('INGEST_TOKEN','')
    provided=request.headers.get('authorization','').removeprefix('Bearer ')
    if not expected or not secrets.compare_digest(expected,provided): raise HTTPException(401,'İçe aktarım kimliği doğrulanamadı')
    with connect() as c:
        return c.execute('SELECT ingest_order(%s) AS result',(Jsonb(data),)).fetchone()['result']

@app.get('/api/carrier/status')
def carrier_status(request:Request):
    from app.carrier import check_connection,CarrierError
    with connect() as c:
        u=actor(request,c)
        if u['role']!='admin':raise HTTPException(403,'Yönetici gerekir')
    try:return check_connection()
    except CarrierError as e:raise HTTPException(503,str(e))

@app.get('/')
def home():return FileResponse(WEB/'index.html')
app.mount('/',StaticFiles(directory=WEB,html=True),name='web')
