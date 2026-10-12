BEGIN;
-- Service-only transport for the owner-private Sites deployment.
CREATE FUNCTION public.gazi_ops_hosted(p_key text,p_operation text,p_data jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=gazi_ops,pg_catalog AS $$
DECLARE v_actor bigint;v_job jobs;v_result jsonb;
BEGIN
 IF nullif(p_key,'') IS NULL OR encode(sha256(convert_to(p_key,'UTF8')),'hex') IS DISTINCT FROM (SELECT value #>> '{}' FROM settings WHERE key='runtime_key_hash') THEN RAISE EXCEPTION 'Runtime kimliği doğrulanamadı'; END IF;
 SELECT id INTO v_actor FROM users WHERE phone='905550009991' AND role='admin' AND active;
 IF v_actor IS NULL THEN RAISE EXCEPTION 'Test yöneticisi tanımlanmadı'; END IF;
 IF p_operation='me' THEN RETURN jsonb_build_object('id',v_actor,'name','Gazi Test Yönetimi','role','admin');
 ELSIF p_operation='rpc' THEN RETURN rpc(v_actor,p_data->>'operation',coalesce(p_data->'data','{}'));
 ELSIF p_operation='job' THEN
  SELECT jsonb_build_object('id',id,'kind',kind,'state',state,'attempts',attempts,'last_error',last_error) INTO v_result FROM jobs WHERE id=(p_data->>'id')::bigint;IF v_result IS NULL THEN RAISE EXCEPTION 'İşlem bulunamadı'; END IF;RETURN v_result;
 ELSIF p_operation='claim' THEN
  PERFORM schedule_tracking();SELECT * INTO v_job FROM claim_job();
  IF v_job.id IS NULL THEN RETURN 'null'; END IF;
  RETURN jsonb_build_object('job',to_jsonb(v_job),'order',(SELECT to_jsonb(o) FROM orders o WHERE siparis_no=v_job.order_id),'shipment',(SELECT to_jsonb(s) FROM shipments s WHERE order_id=v_job.order_id),'label',(SELECT to_jsonb(l) FROM labels l WHERE order_id=v_job.order_id),'mode',(SELECT value FROM settings WHERE key='carrier_mode'));
 ELSIF p_operation='finish' THEN RETURN jsonb_build_object('applied',finish_job((p_data->>'id')::bigint,(p_data->>'lease')::uuid,p_data->'result'));
 ELSIF p_operation='fail' THEN RETURN jsonb_build_object('applied',fail_job((p_data->>'id')::bigint,(p_data->>'lease')::uuid,p_data->>'error'));
 ELSIF p_operation='codes' THEN
  SELECT jsonb_build_object('city_code',c.code,'district_code',d.code) INTO v_result FROM cities c JOIN districts d ON d.city_code=c.code WHERE lower(translate(c.name,'İIÇĞÖŞÜ','iıçğöşü'))=lower(translate(p_data->>'city','İIÇĞÖŞÜ','iıçğöşü')) AND lower(translate(d.name,'İIÇĞÖŞÜ','iıçğöşü'))=lower(translate(p_data->>'district','İIÇĞÖŞÜ','iıçğöşü'));IF v_result IS NULL THEN RAISE EXCEPTION 'İl/ilçe kodu bulunamadı'; END IF;RETURN v_result;
 ELSIF p_operation='connection' THEN RETURN jsonb_build_object('mode',(SELECT value FROM settings WHERE key='carrier_mode'),'message','TEST / SİMÜLASYON · PostgreSQL bağlantısı hazır; gerçek DHL gönderisi oluşturulmaz');
 ELSE RAISE EXCEPTION 'Geçersiz runtime işlemi'; END IF;
END $$;
REVOKE ALL ON FUNCTION public.gazi_ops_hosted(text,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.gazi_ops_hosted(text,text,jsonb) TO service_role;
COMMIT;
