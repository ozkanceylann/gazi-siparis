const {PGlite}=require('@electric-sql/pglite');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const db=new PGlite();await db.exec(fs.readFileSync('database/001_install.sql','utf8'));await db.exec(fs.readFileSync('database/002_ingest.sql','utf8'));
 console.log('PL/pgSQL schema installed');
 await db.exec("insert into gazi_ops.users(phone,name,password_hash,role) values('905550001111','Admin','disabled','admin'),('905550002222','Seller','disabled','seller'),('905550003333','Other','disabled','seller')");
 async function sql(s,p=[]){return (await db.query(s,p)).rows;}
 async function rpc(actor,op,data={}){return (await sql('select gazi_ops.rpc($1,$2,$3::jsonb) as r',[actor,op,JSON.stringify(data)]))[0].r;}
 const data={request_key:'00000000-0000-0000-0000-000000000001',seller_id:2,ad_soyad:'Test Müşteri',musteri_tel:'0555 111 22 33',adres:'Test mahallesi sokak 10',sehir:'İzmir',ilce:'Konak',urun_bilgisi:'Siyah Gemlik Sele Zeytin',toplam_tutar:1100,packages:[{kg:10,desi:10},{kg:5,desi:5}]};
 const id=(await rpc(1,'create',data)).id;assert.equal((await rpc(1,'create',data)).id,id);
 await assert.rejects(rpc(3,'detail',{id}));await assert.rejects(rpc(2,'prepare',{id,version:1}));await assert.rejects(rpc(1,'prepare',{id,version:99}));
 await rpc(2,'edit',{...data,id,version:1});await rpc(1,'prepare',{id,version:2});await assert.rejects(rpc(2,'edit',{...data,id,version:3}));
 let j=await rpc(1,'cargo',{id});await assert.rejects(rpc(1,'cargo',{id}));
 // Drain optional reaction job, then claim creation.
 let job=(await sql('select * from gazi_ops.claim_job()'))[0];
 if(job.kind==='reaction'){await sql('select gazi_ops.finish_job($1,$2,$3::jsonb)',[job.id,job.lease_token,'{}']);job=(await sql('select * from gazi_ops.claim_job()'))[0];}
 assert.equal(job.kind,'create');assert.equal(job.id,j.job_id);
 const created={reference:'GZTEST-1',tracking:'TEST000001',environment:'mock',status_code:1,state:'Gönderi hazırlandı',state_at:'2026-10-12T10:00:00+03:00',label:{zpl:'^XA^XZ',barcodes:[{barcode:'TEST1-1'},{barcode:'TEST1-2'}]},events:[{id:'a',title:'Gönderi hazırlandı',at:'2026-10-12T10:00:00+03:00'}]};
 await assert.rejects(sql('select gazi_ops.finish_job($1,$2,$3::jsonb)',[job.id,job.lease_token,JSON.stringify({...created,label:{zpl:'x',barcodes:[{barcode:'same'},{barcode:'same'}]}})]));
 assert.equal((await rpc(1,'detail',{id})).order.kargo_durumu,'Hazırlandı');
 assert.equal((await sql('select gazi_ops.finish_job($1,$2,$3::jsonb) as ok',[job.id,'00000000-0000-0000-0000-000000000099',JSON.stringify(created)]))[0].ok,false);
 await sql('select gazi_ops.finish_job($1,$2,$3::jsonb)',[job.id,job.lease_token,JSON.stringify(created)]);
 let d=await rpc(1,'detail',{id});assert.equal(d.order.kargo_durumu,'Kargolandı');assert.equal(d.order.kargo_adet,2);assert.equal(d.order.kargo_kg,15);assert.equal(d.order.has_label,true);
 await assert.rejects(rpc(1,'waiting',{id,version:d.order.version}));
 // Stored-label request cannot create another shipment.
 assert.equal((await rpc(1,'cargo',{id})).already_created,true);
 async function drain(resultForTrack){for(let k=0;k<10;k++){let x=(await sql('select * from gazi_ops.claim_job()'))[0];if(!x)break;let r=x.kind==='reaction'?{}:x.kind==='cancel'?{cancelled:true}:resultForTrack||created;await sql('select gazi_ops.finish_job($1,$2,$3::jsonb)',[x.id,x.lease_token,JSON.stringify(r)]);}}
 await drain();
 let bulk=await rpc(1,'bulk_track');assert.equal(bulk.queued,1);await drain({...created,reference:'DHL-BRANCH-REF',status_code:4,state:'Dağıtımda',state_at:'2026-10-12T11:00:00+03:00',branch:'Konak',branch_phone:'02320000000',events:[{id:'b',title:'Dağıtımda',at:'2026-10-12T11:00:00+03:00'}]});
 d=await rpc(1,'detail',{id});assert.equal(d.order.kargo_referans,'DHL-BRANCH-REF');assert.equal(d.order.sube_tel,'02320000000');
 await rpc(1,'track',{id});await drain({...created,reference:'DHL-BRANCH-REF',status_code:2,state:'Eski hareket',state_at:'2026-10-12T09:00:00+03:00'});assert.equal((await rpc(1,'detail',{id})).order.shipmentStatusCode,4);
 await rpc(1,'track',{id});await drain({...created,reference:'DHL-BRANCH-REF',status_code:5,state:'Teslim Edildi',state_at:'2026-10-12T12:00:00+03:00'});assert.equal((await rpc(1,'detail',{id})).order.kargo_durumu,'Tamamlandı');
 await rpc(1,'track',{id});await drain({...created,reference:'DHL-BRANCH-REF',status_code:2,state_at:'2026-10-12T13:00:00+03:00'});assert.equal((await rpc(1,'detail',{id})).order.shipmentStatusCode,5);
 assert.equal((await rpc(1,'report',{tab:'all'})).by_status[0].count,1);
 let list=await rpc(1,'list',{tab:'tamamlandi',query:'Test Müşteri'});assert.equal(list.total,1);assert.equal(list.amount,1100);assert.equal((await rpc(3,'list')).total,0);
 await assert.rejects(rpc(1,'report',{start:'2026-10-20',end:'2026-10-01'}));
 // Cancellation commits only after a successful provider response. Restoration archives labels and increments ref generation.
 const second=(await rpc(1,'create',{...data,request_key:'00000000-0000-0000-0000-000000000002'})).id;
 assert.ok((await rpc(1,'detail',{id:second})).issues.length);
 await rpc(1,'prepare',{id:second,version:1});await rpc(1,'cargo',{id:second});await drain({...created,reference:'GZTEST-2',tracking:'TEST000002'});
 let v=(await rpc(1,'detail',{id:second})).order.version;await rpc(1,'cancel',{id:second,version:v,reason:'Test iptali'});
 assert.equal((await rpc(1,'detail',{id:second})).order.kargo_durumu,'Kargolandı');await drain();
 d=await rpc(1,'detail',{id:second});assert.equal(d.order.kargo_durumu,'İptal');await rpc(1,'restore',{id:second,version:d.order.version});d=await rpc(1,'detail',{id:second});assert.equal(d.order.cargo_attempt,2);assert.equal(d.order.kargo_referans,null);assert.equal(d.order.kargo_durumu,'Bekliyor');
 const third=(await rpc(1,'create',{...data,request_key:'00000000-0000-0000-0000-000000000003',adres:'Yeni adres yeni sokak 20'})).id;
 await rpc(1,'merge',{id:third,version:1,target:second,target_version:d.order.version});assert.equal((await rpc(1,'detail',{id:third})).order.merged_into,second);assert.equal((await rpc(1,'detail',{id:second})).order.adres,'Yeni adres yeni sokak 20');
 const ingest={...data,siparis_tel:'0555 000 22 22',source_order_no:9000};const ir=(await sql('select gazi_ops.ingest_order($1::jsonb) as r',[JSON.stringify(ingest)]))[0].r;assert.equal((await sql('select gazi_ops.ingest_order($1::jsonb) as r',[JSON.stringify(ingest)]))[0].r.id,ir.id);
 await db.exec(fs.readFileSync('database/003_test_seed.sql','utf8'));const total=(await rpc(1,'summary')).total;await db.exec(fs.readFileSync('database/003_test_seed.sql','utf8'));assert.equal((await rpc(1,'summary')).total,total);
 assert.equal((await sql('select gazi_ops.schedule_tracking() as n'))[0].n,0);
 // Bulk must enqueue all pages, not just the first loaded screen.
 await sql("update gazi_ops.shipments set last_sync=now()-interval '1 hour' where status_code<>5");const queued=await rpc(1,'bulk_track');assert.equal(queued.queued,5);
 assert.ok((await sql('select gazi_ops.schedule_tracking() as n'))[0].n>=5);
 assert.equal((await rpc(1,'connection')).mode,'mock');
 assert.equal((await sql("select exists(select 1 from pg_proc p cross join lateral aclexplode(p.proacl) a where p.oid='gazi_ops.rpc(bigint,text,jsonb)'::regprocedure and a.grantee=0 and a.privilege_type='EXECUTE') as p"))[0].p,false);
 console.log('PASS: lifecycle, leases, duplicate shipment guard, packages, stored reference, single/bulk tracking, stale events, delivered state, cancellation/restore, merge, ingest replay, reports, isolation, seed replay, private privileges');
 await db.close();
})().catch(e=>{console.error(e);process.exit(1)});
