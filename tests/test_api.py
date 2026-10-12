import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
class DB:
 def __init__(self,u=None):self.u=u;self.calls=[]
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def execute(self,sql,params=None):self.calls.append((sql,params));return self
 def fetchone(self):
  if self.calls[-1][0].startswith('SELECT rpc'):return {'result':{'ok':True}}
  return self.u
class APITests(unittest.TestCase):
 def setUp(self):self.client=TestClient(app)
 def test_origin(self):
  self.assertEqual(self.client.post('/api/rpc',json={'operation':'list'}).status_code,403)
 def test_no_session(self):
  with patch('app.main.connect',return_value=DB()):r=self.client.post('/api/rpc',json={'operation':'list'},headers={'origin':'http://localhost:8000'})
  self.assertEqual(r.status_code,401)
 def test_csrf(self):
  with patch('app.main.connect',return_value=DB({'id':2,'name':'Test','role':'seller','csrf':'right'})):r=self.client.post('/api/rpc',json={'operation':'list'},headers={'origin':'http://localhost:8000','X-CSRF-Token':'wrong'})
  self.assertEqual(r.status_code,403)
 def test_principal_cannot_be_injected(self):
  db=DB({'id':2,'name':'Test','role':'seller','csrf':'right'})
  with patch('app.main.connect',return_value=db):r=self.client.post('/api/rpc',json={'operation':'edit','data':{'p_actor':1,'seller_id':1}},headers={'origin':'http://localhost:8000','X-CSRF-Token':'right'})
  self.assertEqual(r.status_code,200);self.assertEqual(db.calls[-1][1][0],2)
 def test_public_ingest_disabled(self):
  with patch.dict('os.environ',{'INGEST_TOKEN':''}):self.assertEqual(self.client.post('/api/ingest',json={}).status_code,401)
 def test_static_security_headers(self):
  r=self.client.get('/');self.assertEqual(r.status_code,200);self.assertIn("script-src 'self'",r.headers['Content-Security-Policy']);self.assertIn('Sipariş Sistemi',r.text)
