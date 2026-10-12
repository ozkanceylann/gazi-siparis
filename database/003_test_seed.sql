-- OPTIONAL. Synthetic fixtures only; not executed automatically in Docker.
BEGIN;
SET LOCAL search_path=gazi_ops,pg_catalog;
INSERT INTO users(phone,name,password_hash,role) VALUES('905550009991','TEST Operatörü','login-disabled','admin') ON CONFLICT(phone) DO NOTHING;
DO $$
DECLARE i int;uid bigint;oid bigint;st text;code int;
BEGIN
 SELECT id INTO uid FROM users WHERE phone='905550009991';
 FOR i IN 1..15 LOOP
  st:=CASE WHEN i<=4 THEN 'Bekliyor' WHEN i<=7 THEN 'Hazırlandı' WHEN i<=11 THEN 'Kargolandı' WHEN i<=13 THEN 'Tamamlandı' WHEN i=14 THEN 'İade' ELSE 'İptal' END;
  code:=CASE WHEN i=8 THEN 2 WHEN i=9 THEN 3 WHEN i=10 THEN 4 WHEN i=11 THEN 6 WHEN i IN (12,13) THEN 5 WHEN i=14 THEN 7 END;
  INSERT INTO orders(seller_id,request_key,ad_soyad,musteri_tel,siparis_tel,siparis_alan,adres,sehir,ilce,urun_bilgisi,toplam_tutar,packages,kargo_durumu,notlar)
  VALUES(uid,('10000000-0000-0000-0000-'||lpad(i::text,12,'0'))::uuid,'TEST Müşteri '||i,'905550000000','905550009991','TEST Satıcı','Test Mahallesi Örnek Sokak No 10','İzmir','Konak','Siyah Gemlik Sele Zeytin · TEST',1100,CASE WHEN i=5 THEN '[{"kg":10,"desi":10},{"kg":5,"desi":5}]'::jsonb ELSE '[{"kg":10,"desi":10}]'::jsonb END,st,'GERÇEK SİPARİŞ DEĞİL') ON CONFLICT(request_key) DO NOTHING RETURNING siparis_no INTO oid;
  IF oid IS NULL THEN CONTINUE; END IF;
  PERFORM audit(oid,'TEST · Örnek sipariş oluşturuldu');
  IF code IS NOT NULL THEN
   INSERT INTO shipments(order_id,reference,tracking,environment,status_code,state,state_at,last_sync,branch) VALUES(oid,'GZTEST-SEED-'||oid,'TEST'||oid,'mock',code,'TEST · Kargo durumu '||code,now(),now(),'TEST Şubesi');
   INSERT INTO events(order_id,event_key,title,payload) VALUES(oid,'carrier:seed','TEST · Örnek hareket','{"environment":"mock"}');
  END IF;
  IF i IN (2,11,14) THEN INSERT INTO issues(order_id,kind,title) VALUES(oid,CASE WHEN i=2 THEN 'address' ELSE 'carrier' END,'TEST · Müdahale bekleyen örnek sorun'); END IF;
 END LOOP;
END $$;
COMMIT;
