# Kargo servis sözleşmesi

Worker dış servisi çağırır; dönen sonucu PL/pgSQL `finish_job` uygular. İstek sırasında lease alınır, eski worker cevabı farklı lease'i geçemez. Yeniden denemelerde aynı referans/idempotency anahtarı kullanılır. Bir kez oluşturulan gönderinin barkod ve referansı korunur.

Gateway'e HTTPS POST ve `Authorization: Bearer <sunucu sırrı>` gider. JSON:

```json
{"operation":"create","reference":"GAZI-100-1","idempotency_key":"GAZI-100-1","order":{"siparis_no":100,"packages":[{"kg":10,"desi":10}]},"shipment":null,"payload":{}}
```

`operation`: create, track, label, cancel. `order` bütün sipariş alanlarını içerir; Decimal ve tarihler JSON metni olur. Gateway `create` için aynı idempotency anahtarına aynı gönderiyi döndürmelidir. Bir gönderi bulunamadığı kesin doğrulanmadan ikinci gönderi açmamalıdır. `label` sadece mevcut gönderiden etiketi alır. `track` referans ile sorgular; şubede farklı referans bulunduysa cevabında bu referansı verir.

HTTP 200 cevap:

```json
{
 "reference":"DHL-SUBE-REF-100",
 "tracking":"123456789012",
 "environment":"sandbox",
 "status_code":4,
 "state":"Dağıtımda",
 "state_at":"2026-10-12T11:00:00+03:00",
 "branch":"TEST Şubesi",
 "branch_phone":"",
 "events":[{"id":"event-1","title":"Dağıtımda","at":"2026-10-12T11:00:00+03:00"}],
 "label":{"zpl":"^XA...^XZ","barcodes":[{"pieceNumber":1,"barcode":"123456789012-1"}]}
}
```

`label`, track cevabında isteğe bağlıdır. Paket barkod sayısı ve tekilliği SQL'de doğrulanır. `pdf_base64` varsa geçerli PDF olmalıdır. `movement_error`, durum servisi başarılı fakat hareket servisi başarısız olduğunda kullanılır; boş geçmiş mevcut hareketleri silmez. `cancel` cevabı `{"cancelled":true}` olmalıdır; HTTP 200 tek başına iptal sayılmaz.

Durum kodları: 1 hazırlandı, 2 transfer, 3 teslimat şubesi, 4 dağıtım, 5 teslim, 6 teslim edilemedi, 7 geri geliyor, 8 destek. 7 kodu otomatik takipten çıkarılmaz.

Doğrudan sandbox adaptörü eski Gazi çalışmasında kullanılan DHL REST yollarıyla yeniden yazıldı. Yeni repo testlerinde servis cevapları taklit edildi. Sandbox erişim anahtarları/izin verilen IP olmadan gerçek servis doğrulaması yapılmış sayılmaz. Canlı ortamda yalnızca doğrulanmış normalize gateway kullanılır.
