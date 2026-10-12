BEGIN;
CREATE FUNCTION gazi_ops.ingest_order(p_data jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=gazi_ops,pg_catalog AS $$
DECLARE u users;admin_id bigint;o orders;r jsonb;k uuid;source_no bigint;
BEGIN
 SELECT * INTO u FROM users WHERE phone=phone(p_data->>'siparis_tel') AND active;
 IF u.id IS NULL THEN RAISE EXCEPTION 'Satıcı önce kullanıcı olarak tanımlanmalı'; END IF;
 SELECT id INTO admin_id FROM users WHERE active AND role='admin' ORDER BY id LIMIT 1;
 IF admin_id IS NULL THEN RAISE EXCEPTION 'Yönetici tanımlanmalı'; END IF;
 source_no:=nullif(p_data->>'source_order_no','')::bigint;
 IF source_no IS NULL AND nullif(p_data->>'source_message_id','') IS NULL THEN RAISE EXCEPTION 'Kaynak sipariş no veya mesaj kimliği gerekli'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(coalesce(source_no::text,p_data->>'source_message_id'),1));
 SELECT * INTO o FROM orders WHERE (source_no IS NOT NULL AND source_order_no=source_no) OR (nullif(p_data->>'source_message_id','') IS NOT NULL AND source_message_id=p_data->>'source_message_id');
 IF FOUND THEN RETURN jsonb_build_object('id',o.siparis_no,'replayed',true); END IF;
 k:=gen_random_uuid();r:=rpc(admin_id,'create',p_data||jsonb_build_object('request_key',k,'seller_id',u.id));
 UPDATE orders SET source_order_no=source_no,source_message_id=nullif(p_data->>'source_message_id','') WHERE siparis_no=(r->>'id')::bigint;
 RETURN r;
END $$;
REVOKE ALL ON FUNCTION gazi_ops.ingest_order(jsonb) FROM PUBLIC;
COMMIT;
