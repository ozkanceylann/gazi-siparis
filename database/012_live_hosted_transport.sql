BEGIN;
CREATE FUNCTION public.gazi_live_hosted(p_key text,p_operation text,p_data jsonb DEFAULT '{}') RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=gazi_live,pg_catalog,public AS $$
DECLARE uid bigint;oid bigint;j jobs;o orders;seller users;result jsonb;op text;data jsonb;k uuid;source_ref text;
BEGIN
 IF nullif(p_key,'') IS NULL OR encode(sha256(convert_to(p_key,'UTF8')),'hex') IS DISTINCT FROM (SELECT value #>> '{}' FROM settings WHERE key='runtime_key_hash') THEN RAISE EXCEPTION 'Runtime kimliği doğrulanamadı';END IF;
 SELECT id INTO uid FROM users WHERE phone='905550009991' AND role='admin' AND active;IF uid IS NULL THEN RAISE EXCEPTION 'Yönetici tanımlanmadı';END IF;
 IF p_operation='me' THEN RETURN jsonb_build_object('id',uid,'name','Gazi Yönetim','role','admin','mode','live');
 ELSIF p_operation='rpc' THEN
  op:=p_data->>'operation';data:=coalesce(p_data->'data','{}');oid:=nullif(data->>'id','')::bigint;
  IF op IN ('cargo','retry_label') OR (op='cancel' AND (EXISTS(SELECT 1 FROM shipments WHERE order_id=oid AND cancelled_at IS NULL) OR EXISTS(SELECT 1 FROM orders WHERE siparis_no=oid AND nullif(legacy_snapshot->>'kargo_takip_kodu','') IS NOT NULL))) THEN RAISE EXCEPTION 'Gerçek DHL gönderisi oluşturma, etiket kesme ve kargo iptal yetkileri henüz etkinleştirilmedi';END IF;
  IF op='prepare' AND EXISTS(SELECT 1 FROM shipments WHERE order_id=oid AND cancelled_at IS NULL) THEN RAISE EXCEPTION 'Bu siparişin mevcut kargosu var; takip kaydını kontrol edin';END IF;
  IF op='create' THEN
   k:=(data->>'request_key')::uuid;IF k IS NULL THEN RAISE EXCEPTION 'İstek anahtarı gerekli';END IF;
   PERFORM pg_advisory_xact_lock(hashtextextended(k::text,71));SELECT siparis_no INTO oid FROM orders WHERE request_key=k;IF FOUND THEN RETURN jsonb_build_object('id',oid,'replayed',true);END IF;
   SELECT * INTO seller FROM users WHERE id=(data->>'seller_id')::bigint AND active AND phone ~ '^90[0-9]{10}$';IF seller.id IS NULL THEN RAISE EXCEPTION 'Sipariş alan satıcıyı seçin';END IF;
   PERFORM phone(data->>'musteri_tel');PERFORM validate_packages(data->'packages');
   IF length(trim(coalesce(data->>'ad_soyad','')))<2 OR length(trim(coalesce(data->>'adres','')))<5 OR length(trim(coalesce(data->>'sehir','')))<2 OR length(trim(coalesce(data->>'ilce','')))<2 OR coalesce((data->>'toplam_tutar')::numeric,-1)<0 THEN RAISE EXCEPTION 'Sipariş alanları eksik veya tutar geçersiz';END IF;
   INSERT INTO public.tum_siparisler(siparis_tel,ad_soyad,musteri_tel,adres,urun_bilgisi,sehir,ilce,toplam_tutar,odeme_sekli,notlar,tarih,firma,siparis_alan,kargo_durumu,kargo_adet,kargo_kg)
   VALUES(seller.phone,data->>'ad_soyad',phone(data->>'musteri_tel'),data->>'adres',data->>'urun_bilgisi',data->>'sehir',data->>'ilce',data->>'toplam_tutar',data->>'odeme_sekli',data->>'notlar',now() AT TIME ZONE 'Europe/Istanbul','gazi',seller.name,'Bekliyor',jsonb_array_length(data->'packages')::text,(SELECT string_agg(p->>'kg',',') FROM jsonb_array_elements(data->'packages')p)) RETURNING siparis_no,kargo_siparis_no INTO oid,source_ref;
   PERFORM set_config('gazi_live.request_key',k::text,true);
   INSERT INTO public.gazi_siparisler(siparis_no,siparis_tel,ad_soyad,musteri_tel,adres,urun_bilgisi,sehir,ilce,sehir_kodu,ilce_kodu,toplam_tutar,odeme_sekli,notlar,tarih,firma,siparis_alan,kargo_durumu,kargo_adet,kargo_kg,kargo_siparis_no,musteri_no)
   SELECT siparis_no,siparis_tel,ad_soyad,musteri_tel,adres,urun_bilgisi,sehir,ilce,sehir_kodu,ilce_kodu,toplam_tutar,odeme_sekli,notlar,tarih,firma,siparis_alan,kargo_durumu,kargo_adet,kargo_kg,coalesce(source_ref,'GLIVE-'||oid||'-1'),musteri_no FROM public.tum_siparisler WHERE siparis_no=oid;
   PERFORM set_config('gazi_live.request_key','',true);
   UPDATE orders SET packages=data->'packages' WHERE siparis_no=oid;PERFORM audit(oid,'Sipariş yeni panelden oluşturuldu',uid);
   RETURN jsonb_build_object('id',oid);
  ELSIF op='users' THEN SELECT coalesce(jsonb_agg(jsonb_build_object('id',id,'name',name,'phone',phone,'role',role) ORDER BY name),'[]') INTO result FROM users WHERE active AND role='seller' AND phone ~ '^90[0-9]{10}$';RETURN result;
  ELSIF op='label' THEN result:=cached_label(oid);IF result IS NULL THEN RAISE EXCEPTION 'Etiket bulunamadı; mevcut DHL gönderisinin etiketi yeniden alınmalı';END IF;RETURN result;
  END IF;
  IF oid IS NOT NULL AND op IN ('edit','prepare','waiting','cargo','cancel','restore','hide','codes','retry_label','merge') THEN
   PERFORM 1 FROM public.gazi_siparisler WHERE siparis_no IN (oid,coalesce((data->>'target')::bigint,oid)) ORDER BY siparis_no FOR UPDATE;
  END IF;
  IF op IN ('prepare','cargo') THEN PERFORM validate_shipping(oid);END IF;
  RETURN rpc(uid,op,data);
 ELSIF p_operation='job' THEN SELECT jsonb_build_object('id',id,'kind',kind,'state',state,'attempts',attempts,'last_error',last_error) INTO result FROM jobs WHERE id=(p_data->>'id')::bigint;IF result IS NULL THEN RAISE EXCEPTION 'İşlem bulunamadı';END IF;RETURN result;
 ELSIF p_operation='claim' THEN
  PERFORM schedule_tracking();SELECT * INTO j FROM claim_job();IF j.id IS NULL THEN RETURN 'null';END IF;
  RETURN jsonb_build_object('job',to_jsonb(j),'order',(SELECT to_jsonb(x) FROM orders x WHERE siparis_no=j.order_id),'shipment',(SELECT to_jsonb(x) FROM shipments x WHERE order_id=j.order_id),'label',cached_label(j.order_id),'mode','live');
 ELSIF p_operation='finish' THEN
  SELECT order_id INTO oid FROM jobs WHERE id=(p_data->>'id')::bigint;PERFORM 1 FROM public.gazi_siparisler WHERE siparis_no=oid FOR UPDATE;
  result:=jsonb_build_object('applied',finish_job((p_data->>'id')::bigint,(p_data->>'lease')::uuid,p_data->'result'));IF (result->>'applied')::boolean THEN UPDATE shipments SET reference_verified=coalesce((p_data->'result'->>'reference_verified')::boolean,reference_verified) WHERE order_id=oid;PERFORM writeback(oid);END IF;RETURN result;
 ELSIF p_operation='fail' THEN RETURN jsonb_build_object('applied',fail_job((p_data->>'id')::bigint,(p_data->>'lease')::uuid,p_data->>'error'));
 ELSIF p_operation='codes' THEN
  SELECT jsonb_build_object('city_code',c.code,'district_code',d.code) INTO result FROM cities c JOIN districts d ON d.city_code=c.code WHERE lower(translate(c.name,'İIÇĞÖŞÜ','iıçğöşü'))=lower(translate(p_data->>'city','İIÇĞÖŞÜ','iıçğöşü')) AND lower(translate(d.name,'İIÇĞÖŞÜ','iıçğöşü'))=lower(translate(p_data->>'district','İIÇĞÖŞÜ','iıçğöşü'));IF result IS NULL THEN RAISE EXCEPTION 'İl/ilçe kodları bulunamadı';END IF;RETURN result;
 ELSIF p_operation='gateway' THEN RETURN (SELECT value FROM settings WHERE key='gateway');
 ELSE RAISE EXCEPTION 'Geçersiz runtime işlemi';END IF;
END $$;
REVOKE ALL ON FUNCTION public.gazi_live_hosted(text,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.gazi_live_hosted(text,text,jsonb) TO service_role;
COMMIT;
