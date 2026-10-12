BEGIN;
SET LOCAL search_path=gazi_live,pg_catalog;
CREATE FUNCTION safe_json(p text) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=gazi_live,pg_catalog AS $$ BEGIN RETURN coalesce(nullif(p,''),'{}')::jsonb;EXCEPTION WHEN others THEN RETURN '{}';END $$;
CREATE FUNCTION amount(p text) RETURNS numeric LANGUAGE plpgsql IMMUTABLE SET search_path=gazi_live,pg_catalog AS $$
DECLARE v text:=regexp_replace(coalesce(p,''),'(TL|TRY|₺|\s)','','gi');
BEGIN
 IF v ~ '^(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$' THEN v:=replace(replace(v,'.',''),',','.');ELSIF v !~ '^\d+(\.\d{1,2})?$' THEN RETURN NULL;END IF;
 RETURN v::numeric;EXCEPTION WHEN others THEN RETURN NULL;
END $$;
CREATE FUNCTION legacy_phone(p text) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=gazi_live,pg_catalog AS $$ BEGIN RETURN phone(p);EXCEPTION WHEN others THEN RETURN coalesce(p,'');END $$;
CREATE FUNCTION legacy_packages(p_count text,p_kg text) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=gazi_live,pg_catalog AS $$
DECLARE n int:=CASE WHEN p_count ~ '^\d+$' THEN greatest(1,least(100,p_count::int)) ELSE 1 END;vs text[];v numeric;out jsonb:='[]';i int;
BEGIN
 vs:=regexp_split_to_array(regexp_replace(coalesce(p_kg,''),'(kg|\s)','','gi'),'[,+;-]');
 FOR i IN 1..n LOOP v:=coalesce(amount(vs[least(i,array_length(vs,1))]),10);IF v<=0 THEN v:=10;END IF;out:=out||jsonb_build_array(jsonb_build_object('kg',v,'desi',v));END LOOP;RETURN out;
END $$;
CREATE FUNCTION import_source(p jsonb) RETURNS void LANGUAGE plpgsql SET search_path=gazi_live,pg_catalog AS $$
DECLARE oid bigint:=(p->>'siparis_no')::bigint;uid bigint;who text;st text;pkg jsonb;raw jsonb;snapshot jsonb;ref text;tracking_no text;code int;old orders;event jsonb;seq text;eventat timestamptz;body jsonb;
BEGIN
 PERFORM set_config('gazi_live.importing','1',true);
 who:=legacy_phone(p->>'siparis_tel');IF who='' THEN who:='legacy:unknown';END IF;
 INSERT INTO users(phone,name,password_hash,role) VALUES(who,coalesce(nullif(p->>'siparis_alan',''),'Satıcı'),'login-disabled','seller') ON CONFLICT(phone) DO NOTHING;
 SELECT id INTO uid FROM users WHERE phone=who;
 SELECT * INTO old FROM orders WHERE siparis_no=oid;
 raw:=safe_json(p->>'kargo_api_yanit');pkg:=CASE WHEN old.siparis_no IS NOT NULL AND old.legacy_snapshot->>'kargo_adet' IS NOT DISTINCT FROM p->>'kargo_adet' AND old.legacy_snapshot->>'kargo_kg' IS NOT DISTINCT FROM p->>'kargo_kg' THEN old.packages ELSE legacy_packages(p->>'kargo_adet',p->>'kargo_kg') END;
 snapshot:=(p-'zpl_base64'-'kargo_zpl'-'kargo_api_yanit')||jsonb_build_object('source_environment',coalesce(raw->>'environment','production'));
 st:=CASE WHEN coalesce((p->>'isDelivered')::boolean,false) OR p->>'shipmentStatusCode'='5' OR p->>'kargo_durumu'='Tamamlandı' THEN 'Tamamlandı' WHEN p->>'shipmentStatusCode'='7' THEN 'İade' ELSE coalesce(nullif(p->>'kargo_durumu',''),'Bekliyor') END;
 IF p->>'kargo_durumu' IN ('İptal','Silindi') THEN st:=p->>'kargo_durumu';END IF;
 IF old.kargo_durumu='Tamamlandı' AND st NOT IN ('İptal','Silindi') THEN st:='Tamamlandı';END IF;
 IF st NOT IN ('Bekliyor','Hazırlandı','Kargolandı','Tamamlandı','İade','İptal','Silindi') THEN st:='Bekliyor';END IF;
 INSERT INTO orders(siparis_no,seller_id,request_key,source_order_no,legacy_snapshot,ad_soyad,musteri_tel,siparis_tel,siparis_alan,adres,sehir,ilce,sehir_kodu,ilce_kodu,urun_bilgisi,toplam_tutar,odeme_sekli,notlar,packages,kargo_durumu,tarih,iptal_nedeni,iptal_tarihi)
 VALUES(oid,uid,coalesce(nullif(current_setting('gazi_live.request_key',true),'')::uuid,md5('gazi-live:'||oid)::uuid),oid,snapshot,coalesce(p->>'ad_soyad',''),legacy_phone(p->>'musteri_tel'),who,coalesce(p->>'siparis_alan',''),coalesce(p->>'adres',''),coalesce(p->>'sehir',''),coalesce(p->>'ilce',''),CASE WHEN p->>'sehir_kodu' ~ '^\d+$' THEN (p->>'sehir_kodu')::int END,CASE WHEN p->>'ilce_kodu' ~ '^\d+$' THEN (p->>'ilce_kodu')::int END,coalesce(p->>'urun_bilgisi',''),coalesce(amount(p->>'toplam_tutar'),0),coalesce(p->>'odeme_sekli',''),coalesce(p->>'notlar',''),pkg,st,coalesce((p->>'tarih')::timestamp AT TIME ZONE 'Europe/Istanbul',now()),p->>'iptal_nedeni',(p->>'iptal_tarihi')::timestamp AT TIME ZONE 'Europe/Istanbul')
 ON CONFLICT(siparis_no) DO UPDATE SET seller_id=excluded.seller_id,legacy_snapshot=excluded.legacy_snapshot,ad_soyad=excluded.ad_soyad,musteri_tel=excluded.musteri_tel,siparis_tel=excluded.siparis_tel,siparis_alan=excluded.siparis_alan,adres=excluded.adres,sehir=excluded.sehir,ilce=excluded.ilce,sehir_kodu=excluded.sehir_kodu,ilce_kodu=excluded.ilce_kodu,urun_bilgisi=excluded.urun_bilgisi,toplam_tutar=excluded.toplam_tutar,odeme_sekli=excluded.odeme_sekli,notlar=excluded.notlar,packages=excluded.packages,kargo_durumu=excluded.kargo_durumu,iptal_nedeni=excluded.iptal_nedeni,iptal_tarihi=excluded.iptal_tarihi,version=orders.version+1,updated_at=now();
 ref:=coalesce(nullif(p->>'kargo_siparis_no',''),nullif(raw->'tracking'->>'referenceId',''));tracking_no:=nullif(p->>'kargo_takip_kodu','');
 code:=CASE WHEN st='Tamamlandı' THEN 5 ELSE nullif(p->>'shipmentStatusCode','')::int END;
 IF ref IS NOT NULL AND tracking_no IS NOT NULL AND st NOT IN ('Silindi') THEN
  IF EXISTS(SELECT 1 FROM shipments WHERE order_id<>oid AND (reference=ref OR tracking=tracking_no)) THEN
   INSERT INTO issues(order_id,kind,title) VALUES(oid,'legacy-reference','Bu kargo referansı başka siparişe de yazılmış; yeni kargo oluşturmayın') ON CONFLICT(order_id,kind) WHERE state='open' DO NOTHING;
  ELSE
   body:=coalesce(raw->'tracking','{}');
   INSERT INTO shipments(order_id,reference,tracking,environment,status_code,state,state_at,last_sync,branch,branch_phone,cancelled_at)
   VALUES(oid,ref,tracking_no,CASE WHEN raw->>'environment'='test' THEN 'sandbox' ELSE 'live' END,coalesce(code,1),coalesce(nullif(p->>'shipmentStatus',''),'Kargo durumu bekleniyor'),NULL,now(),coalesce(body->>'branch',body->>'branchName'),coalesce(body->>'branchPhone',body->>'locationPhone'),CASE WHEN st='İptal' THEN now() END)
   ON CONFLICT(order_id) DO UPDATE SET reference=excluded.reference,tracking=excluded.tracking,status_code=excluded.status_code,state=excluded.state,last_sync=excluded.last_sync,branch=coalesce(excluded.branch,shipments.branch),branch_phone=coalesce(excluded.branch_phone,shipments.branch_phone),cancelled_at=excluded.cancelled_at;
  END IF;
 END IF;
 IF old.siparis_no IS NULL THEN PERFORM audit(oid,'Canlı Gazi siparişi aktarıldı',NULL,jsonb_build_object('source_order_no',oid));END IF;
 IF st IN ('Bekliyor','Hazırlandı') AND (amount(p->>'toplam_tutar') IS NULL OR length(coalesce(p->>'adres',''))<5 OR legacy_phone(p->>'musteri_tel') !~ '^90[0-9]{10}$') THEN
  INSERT INTO issues(order_id,kind,title) VALUES(oid,'legacy-data','Siparişin fiyat, müşteri telefonu veya adres bilgisi kontrol edilmeli') ON CONFLICT(order_id,kind) WHERE state='open' DO NOTHING;
 ELSE UPDATE issues SET state='resolved',resolution='Kaynak bilgileri düzeltildi',resolved_at=now() WHERE order_id=oid AND kind='legacy-data' AND state='open';END IF;
 IF code IN (6,7,8) AND st<>'Tamamlandı' THEN INSERT INTO issues(order_id,kind,title) VALUES(oid,'carrier',coalesce(nullif(p->>'shipmentStatus',''),'Kargo müdahale gerektiriyor')) ON CONFLICT(order_id,kind) WHERE state='open' DO UPDATE SET title=excluded.title;END IF;
 IF nullif(p->>'gonder_hata_bilgisi','') IS NOT NULL THEN INSERT INTO issues(order_id,kind,title) VALUES(oid,'source-error',left(p->>'gonder_hata_bilgisi',500)) ON CONFLICT(order_id,kind) WHERE state='open' DO UPDATE SET title=excluded.title;END IF;
 FOR event IN SELECT * FROM jsonb_array_elements(CASE WHEN jsonb_typeof(body->'movements')='array' THEN body->'movements' ELSE '[]' END) LOOP
  seq:=coalesce(event->>'eventSequence',event->>'id',md5(event::text));BEGIN eventat:=coalesce(event->>'eventDateTime2',event->>'eventDateTime',event->>'at')::timestamptz;EXCEPTION WHEN others THEN eventat:=now();END;
  INSERT INTO events(order_id,event_key,title,occurred_at,payload) VALUES(oid,'legacy-movement:'||seq,coalesce(event->>'eventStatus',event->>'description',event->>'title','Kargo hareketi'),coalesce(eventat,now()),event) ON CONFLICT DO NOTHING;
 END LOOP;
 PERFORM set_config('gazi_live.importing','0',true);
END $$;
CREATE FUNCTION source_to_live() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=gazi_live,pg_catalog AS $$
BEGIN IF current_setting('gazi_live.writeback',true)='1' THEN RETURN NEW;END IF;PERFORM import_source(to_jsonb(NEW));RETURN NEW;END $$;
CREATE FUNCTION writeback(p_id bigint) RETURNS void LANGUAGE plpgsql SET search_path=gazi_live,pg_catalog AS $$
DECLARE o orders;s shipments;l labels;r text;
BEGIN
 SELECT * INTO o FROM orders WHERE siparis_no=p_id;IF o.siparis_no IS NULL OR o.source_order_no IS NULL THEN RETURN;END IF;
 SELECT * INTO s FROM shipments WHERE order_id=p_id;SELECT * INTO l FROM labels WHERE order_id=p_id;
 r:=coalesce(s.reference,o.legacy_snapshot->>'kargo_siparis_no',CASE WHEN o.cargo_attempt>1 THEN 'GLIVE-'||p_id||'-'||o.cargo_attempt END);
 PERFORM set_config('gazi_live.writeback','1',true);
 UPDATE public.gazi_siparisler SET ad_soyad=o.ad_soyad,musteri_tel=o.musteri_tel,adres=o.adres,sehir=o.sehir,ilce=o.ilce,sehir_kodu=o.sehir_kodu::text,ilce_kodu=o.ilce_kodu::text,urun_bilgisi=o.urun_bilgisi,toplam_tutar=o.toplam_tutar::text,odeme_sekli=o.odeme_sekli,notlar=o.notlar,kargo_adet=o.kargo_adet::text,kargo_kg=(SELECT string_agg(p->>'kg',',' ORDER BY n) FROM jsonb_array_elements(o.packages) WITH ORDINALITY AS a(p,n)),kargo_durumu=o.kargo_durumu,iptal_nedeni=o.iptal_nedeni,iptal_tarihi=o.iptal_tarihi AT TIME ZONE 'Europe/Istanbul',kargo_siparis_no=r,kargo_takip_kodu=coalesce(s.tracking,kargo_takip_kodu),"shipmentStatusCode"=coalesce(s.status_code,"shipmentStatusCode"),"shipmentStatus"=coalesce(s.state,"shipmentStatus"),"isDelivered"=(o.kargo_durumu='Tamamlandı'),kargo_gunc_saat=coalesce(s.last_sync::text,kargo_gunc_saat),kargo_zpl=coalesce(l.zpl,kargo_zpl),zpl_base64=coalesce(l.pdf_base64,zpl_base64)
 WHERE siparis_no=o.source_order_no;
 PERFORM set_config('gazi_live.importing','1',true);
 UPDATE orders SET legacy_snapshot=(SELECT (to_jsonb(src)-'zpl_base64'-'kargo_zpl'-'kargo_api_yanit')||jsonb_build_object('source_environment',coalesce(safe_json(src.kargo_api_yanit)->>'environment','production')) FROM public.gazi_siparisler src WHERE siparis_no=p_id) WHERE siparis_no=p_id;
 PERFORM set_config('gazi_live.importing','0',true);
 PERFORM set_config('gazi_live.writeback','0',true);
END $$;
CREATE FUNCTION live_to_source() RETURNS trigger LANGUAGE plpgsql SET search_path=gazi_live,pg_catalog AS $$
BEGIN IF current_setting('gazi_live.importing',true)='1' THEN RETURN NEW;END IF;PERFORM writeback(NEW.siparis_no);RETURN NEW;END $$;
CREATE TRIGGER gazi_plpgsql_source_sync AFTER INSERT OR UPDATE ON public.gazi_siparisler FOR EACH ROW EXECUTE FUNCTION source_to_live();
CREATE TRIGGER live_source_writeback AFTER UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION live_to_source();
CREATE FUNCTION cached_label(p_id bigint) RETURNS jsonb LANGUAGE plpgsql SET search_path=gazi_live,pg_catalog AS $$
DECLARE l labels;p public.gazi_siparisler;r jsonb;b jsonb;
BEGIN
 SELECT * INTO l FROM labels WHERE order_id=p_id;IF l.order_id IS NOT NULL THEN RETURN jsonb_build_object('zpl',l.zpl,'pdf_base64',l.pdf_base64,'barcodes',l.barcodes);END IF;
 SELECT * INTO p FROM public.gazi_siparisler WHERE siparis_no=p_id;
 IF p.zpl_base64 LIKE 'JVBER%' THEN RETURN jsonb_build_object('pdf_base64',p.zpl_base64,'zpl',p.kargo_zpl,'barcodes','[]'::jsonb);END IF;
 r:=safe_json(p.kargo_api_yanit);b:=coalesce(r->'labels',r->'barcodes','[]');
 IF nullif(p.kargo_zpl,'') IS NOT NULL THEN RETURN jsonb_build_object('zpl',p.kargo_zpl,'barcodes',b);END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION validate_shipping(p_id bigint) RETURNS void LANGUAGE plpgsql SET search_path=gazi_live,pg_catalog AS $$
DECLARE o orders;
BEGIN
 SELECT * INTO o FROM orders WHERE siparis_no=p_id;
 IF o.legacy_snapshot->>'source_environment'='test' THEN RAISE EXCEPTION 'Eski test kaydı canlı hesaba gönderilemez';END IF;
 IF length(trim(o.ad_soyad))<2 OR length(trim(o.adres))<5 OR length(trim(o.sehir))<2 OR length(trim(o.ilce))<2 OR o.musteri_tel !~ '^905[0-9]{9}$' THEN RAISE EXCEPTION 'Müşteri adı, telefon ve adres bilgilerini düzeltin';END IF;
 IF o.legacy_snapshot ? 'toplam_tutar' AND amount(o.legacy_snapshot->>'toplam_tutar') IS NULL THEN RAISE EXCEPTION 'Fiyat boş/geçersiz; siparişi düzenleyip fiyatı kaydedin';END IF;
 IF nullif(o.legacy_snapshot->>'kargo_takip_kodu','') IS NOT NULL AND NOT EXISTS(SELECT 1 FROM shipments WHERE order_id=p_id) THEN RAISE EXCEPTION 'Mevcut kargo var; referansı doğrulanmadan yeni gönderi açılamaz';END IF;
 IF EXISTS(SELECT 1 FROM issues WHERE order_id=p_id AND kind='legacy-reference' AND state='open') THEN RAISE EXCEPTION 'Bu kargo başka kayda da bağlı; destek kaydını çözün';END IF;
 PERFORM validate_packages(o.packages);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA gazi_live FROM PUBLIC;
COMMIT;
