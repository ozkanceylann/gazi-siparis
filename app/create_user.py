import argparse,getpass
from app.db import connect
from app.security import password_hash
p=argparse.ArgumentParser();p.add_argument('--phone',required=True);p.add_argument('--name',required=True);p.add_argument('--role',choices=['admin','seller'],default='seller');args=p.parse_args()
pw=getpass.getpass('Şifre (en az 12 karakter): ')
if len(pw)<12:raise SystemExit('Şifre en az 12 karakter olmalı')
if getpass.getpass('Şifre tekrar: ')!=pw:raise SystemExit('Şifreler eşleşmiyor')
with connect() as c:
    c.execute('INSERT INTO users(phone,name,password_hash,role) VALUES(phone(%s),%s,%s,%s)',(args.phone,args.name,password_hash(pw),args.role))
print('Kullanıcı oluşturuldu.')
