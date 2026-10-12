"""Load verified DHL city/district CSV files into the NEW database only."""
import argparse,csv
from app.db import connect
p=argparse.ArgumentParser();p.add_argument('--cities',required=True);p.add_argument('--districts',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
with open(a.cities,encoding='utf-8-sig',newline='') as f:cities=list(csv.DictReader(f))
with open(a.districts,encoding='utf-8-sig',newline='') as f:districts=list(csv.DictReader(f))
for x in cities:int(x['code']);assert x['name'].strip()
for x in districts:int(x['code']);int(x['city_code']);assert x['name'].strip()
print(f'{len(cities)} şehir ve {len(districts)} ilçe doğrulandı.')
if a.apply:
 with connect() as c:
  for x in cities:c.execute('INSERT INTO cities VALUES(%s,%s) ON CONFLICT(code) DO UPDATE SET name=excluded.name',(int(x['code']),x['name'].strip()))
  for x in districts:c.execute('INSERT INTO districts VALUES(%s,%s,%s) ON CONFLICT(city_code,code) DO UPDATE SET name=excluded.name',(int(x['code']),int(x['city_code']),x['name'].strip()))
 print('Yeni veritabanına yüklendi.')
else:print('Ön kontrol tamamlandı; kayıt yazılmadı. Yüklemek için --apply kullanın.')
