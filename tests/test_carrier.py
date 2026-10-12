import unittest,os
from unittest.mock import patch
from datetime import datetime,timezone
from app.carrier import process,dhl_payload,stamp,CarrierError
from app.security import password_hash,verify_password

class CarrierTests(unittest.TestCase):
 def setUp(self):
  self.o={'siparis_no':100,'cargo_attempt':2,'toplam_tutar':1100,'odeme_sekli':'Kapıda ödeme','packages':[{'kg':10,'desi':10},{'kg':5,'desi':5}],'urun_bilgisi':'TEST Zeytin','sehir_kodu':None,'ilce_kodu':None,'sehir':'İzmir','ilce':'Konak','adres':'TEST Adres','ad_soyad':'TEST Müşteri','musteri_tel':'905550000000'}
  self.env={'CARRIER_MODE':'sandbox','DHL_CLIENT_ID':'TEST','DHL_CLIENT_SECRET':'TEST','DHL_CUSTOMER_NUMBER':'TEST','DHL_PASSWORD':'TEST','CARRIER_GATEWAY_URL':'','LABELARY_ENABLED':'false'}
 def test_password(self):
  h=password_hash('test-long-password');self.assertTrue(verify_password('test-long-password',h));self.assertFalse(verify_password('incorrect',h))
 def test_packages_and_cod(self):
  with patch.dict(os.environ,self.env):p=dhl_payload(self.o,'REF')
  self.assertEqual(len(p['orderPieceList']),2);self.assertEqual(p['order']['isCOD'],1)
  self.o['odeme_sekli']='Havale'
  with patch.dict(os.environ,self.env):p=dhl_payload(self.o,'REF')
  self.assertEqual(p['order']['codAmount'],0)
 def test_mock_restored_reference(self):
  with patch.dict(os.environ,{'CARRIER_MODE':'mock'}):r=process({'kind':'create'},self.o,None,None)
  self.assertEqual(r['reference'],'GZTEST-100-2');self.assertEqual(r['environment'],'mock');self.assertEqual(len(r['label']['barcodes']),2)
 def test_create_recovery_does_not_create_order(self):
  calls=[]
  def fake(url,method='GET',body=None,headers=None):
   calls.append(url)
   if url.endswith('/token'):return 200,{'jwt':'TEST'}
   if '/getorder/' in url:return 200,{'orderInvoiceId':'existing'}
   if url.endswith('/createbarcode'):return 200,[{'shipmentId':'123','barcodes':[{'pieceNumber':1,'barcode':'b1','value':'^XA^XZ'},{'pieceNumber':2,'barcode':'b2','value':'^XA^XZ'}]}]
   raise AssertionError(url)
  with patch.dict(os.environ,self.env),patch('app.carrier.http',side_effect=fake):r=process({'kind':'create'},self.o,None,None)
  self.assertFalse(any('/createOrder' in x for x in calls));self.assertEqual(r['tracking'],'123');self.assertEqual(r['label']['zpl'],'^XA^XZ\n^XA^XZ')
 def test_failed_lookup_does_not_create(self):
  with patch.dict(os.environ,self.env),patch('app.carrier.http',side_effect=[(200,{'jwt':'TEST'}),(429,{})]) as http:
   with self.assertRaises(CarrierError):process({'kind':'create'},self.o,None,None)
   self.assertEqual(http.call_count,2)
 def test_track_uses_saved_reference_and_sorts_events(self):
  s={'reference':'BRANCH-NEW-REF','tracking':'123','environment':'sandbox'};calls=[]
  def fake(url,method='GET',body=None,headers=None):
   calls.append(url)
   if url.endswith('/token'):return 200,{'jwt':'TEST'}
   if '/getshipmentstatus/' in url:return 200,{'referenceId':'NEWER-REF','shipmentStatusCode':4,'shipmentStatus':'Dağıtımda'}
   return 200,[{'eventSequence':2,'eventStatus':'Dağıtımda','eventDateTime':'12.10.2026 11:00:00','location':'Latest','locationPhone':'02320000000'},{'eventSequence':1,'eventStatus':'Yolda','eventDateTime':'12.10.2026 09:00:00','location':'Old'}]
  with patch.dict(os.environ,self.env),patch('app.carrier.http',side_effect=fake):r=process({'kind':'track'},self.o,s,None)
  self.assertTrue(all('BRANCH-NEW-REF' in u for u in calls[1:]));self.assertEqual(r['reference'],'NEWER-REF');self.assertEqual(r['branch'],'Latest');self.assertEqual(r['events'][0]['id'],'1')
 def test_environment_mismatch(self):
  with patch.dict(os.environ,{'CARRIER_MODE':'sandbox'}):
   with self.assertRaises(CarrierError):process({'kind':'track'},self.o,{'environment':'mock'},None)
 def test_timestamp(self):
  self.assertEqual(stamp('12.10.2026 11:22:33'),'2026-10-12T11:22:33+03:00');self.assertIsNone(stamp('broken'))

if __name__=='__main__':unittest.main()
