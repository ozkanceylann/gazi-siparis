import os,time,logging
from psycopg.types.json import Jsonb
from app.db import connect
from app.carrier import process,CarrierError
logging.basicConfig(level=logging.INFO)
log=logging.getLogger('gazi.worker')

def tick():
    with connect() as c:
        c.execute("UPDATE settings SET value=%s WHERE key='carrier_mode'",(Jsonb(os.environ.get('CARRIER_MODE','mock')),))
        c.execute('SELECT schedule_tracking()')
        job=c.execute('SELECT * FROM claim_job()').fetchone()
    if not job:return False
    try:
        with connect() as c:
            o=c.execute('SELECT * FROM orders WHERE siparis_no=%s',(job['order_id'],)).fetchone()
            s=c.execute('SELECT * FROM shipments WHERE order_id=%s',(job['order_id'],)).fetchone()
            l=c.execute('SELECT * FROM labels WHERE order_id=%s',(job['order_id'],)).fetchone()
        result=process(job,o,s,l)
        with connect() as c:c.execute('SELECT finish_job(%s,%s,%s)',(job['id'],job['lease_token'],Jsonb(result)))
    except Exception as exc:
        # Only controlled, sanitized messages enter the database; never raw secrets/payloads.
        msg=str(exc) if isinstance(exc,CarrierError) else 'Kargo servisi işlemi tamamlanamadı; bağlantıyı kontrol edin'
        log.warning('Kargo işi başarısız: id=%s kind=%s',job['id'],job['kind'])
        with connect() as c:c.execute('SELECT fail_job(%s,%s,%s)',(job['id'],job['lease_token'],msg))
    return True

if __name__=='__main__':
    while True:
        try: busy=tick()
        except Exception: log.warning('Worker veritabanına ulaşamadı');busy=False
        time.sleep(1 if busy else 10)
