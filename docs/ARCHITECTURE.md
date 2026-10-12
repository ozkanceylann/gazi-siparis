# Mimari

Tarayıcı → aynı origin FastAPI (HttpOnly session + CSRF) → `gazi_ops.rpc` (PL/pgSQL) → PostgreSQL.

Worker → `schedule_tracking` → `claim_job` (FOR UPDATE SKIP LOCKED + süreli lease) → DHL sandbox veya HTTPS gateway → `finish_job` / `fail_job`.

İş kararları veritabanında: sipariş validasyonu, yetki/kayıt sahipliği, aşama/sürüm kontrolü, hazırlama, iş kuyruğu tekilliği, kargo sonucu uygulama, iptal/geri alma, birleştirme, raporlar, takip zamanlaması ve olay geçmişi. Python yalnızca oturum ve dış servis taşıma katmanıdır. HTML/CSS/JavaScript ekranları çizer; PL/pgSQL tarayıcıda arayüz dili olarak çalışmaz.

Tablolar private `gazi_ops` şemasındadır. RLS etkin; PUBLIC yetkileri kapalı. Sunucu DB sahibiyle bağlanır ve yalnızca sabit HTTP operasyon listesini çağırır; veritabanı parolası/JWT/taşıyıcı sırları tarayıcıya verilmez. Bu API'nin dışında ham SQL veya aktör numarası alan herkese açık RPC sunmayın. DB sahibi RLS'yi bypass eder; burada erişim kontrolü `rpc` ve doğrulanmış sunucu oturumuyla sağlanır.

Kimlik bilgilerinden sadece hash tutulur. Yazıcı çıktıları geçici sessionStorage kullanır. Service Worker API cevaplarını önbelleğe almaz. Kaybolan/iptal edilen kayıtlar kalıcı olarak silinmez; sipariş, olay ve gönderi arşivi tutulur.

Gazi UI kaynağı: `ozkanceylann/gazi` main, app.js blob `35ddf1d26201f18b2a47d45eb1da0e264f078434`, style.css blob `46709c86ab9295c26c8a2b2e9b2947a70d4b94e5`. Mevcut CSS korunmuş, uygulama JS ve işlem modeli yeniden yazılmıştır. Sipariş Takip mobil paneli referans alınmamıştır.

Hosted test dağıtımı: Owner-private Sites + platform kimliği → Sites Worker HMAC CSRF → gizli runtime anahtarıyla Supabase Edge → service_role'a özel public.gazi_ops_hosted → PL/pgSQL. Sabit test yöneticisi yalnızca bu owner-private dağıtıma aittir. PostgreSQL tabloları tarayıcıya açılmaz. Anahtar Sites runtime env ve Supabase Vault'ta, DB tarafındaki kontrolü SHA-256 hash ile yapılır. Cron her dakika iş kuyruğunu işler; kargo takip zamanı SQL'de 30 dakika ile sınırlandırılır. Hosted Edge yalnızca mock moduna izin verir; Docker worker sandbox/live gateway adaptörünü içerir.
