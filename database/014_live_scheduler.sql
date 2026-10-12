-- Requires the runtime key stored in Supabase Vault as gazi_ops_runtime_key.
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS pg_net;
SELECT cron.schedule('gazi-live-tracking-worker','* * * * *',$cron$
 SELECT net.http_post(
  url:='https://jarsxtpqzqzhlshpmgot.supabase.co/functions/v1/gazi-live-runtime',
  headers:=jsonb_build_object('Content-Type','application/json','x-gazi-runtime-key',
   (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name='gazi_ops_runtime_key')),
  body:='{"path":"worker"}'::jsonb,timeout_milliseconds:=55000);
$cron$);
