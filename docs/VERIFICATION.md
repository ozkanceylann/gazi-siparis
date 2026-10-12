# Doğrulama — 13 Ekim 2026

`npm test` ve `npm run check` başarılı.

- PL/pgSQL kurulumu ve fonksiyonlar gerçek PostgreSQL motorunu çalıştıran PGlite üzerinde test edildi.
- Sipariş oluşturma/replay; satıcı kapsamı; eski sürüm reddi; yalnızca bekleyen düzenleme; hazırlama; aktif kargo işi tekilliği.
- Lease token kontrolü; yanlış paket barkodlarında transaction geri alma; doğrulanmış sonuçtan sonra Kargolandı.
- Tekli/toplu track; tüm sayfalara ait kayıtların kuyruğa alınması; DHL referans değişikliği; şube telefonu; eski olayın durumu geri düşürmemesi; teslim durumunun korunması.
- Servis cevabından önce iptal olmaması; iptal sonrası kargo/etiket arşivi ve yeni referans denemesi; bekleyen çift kayıt birleştirme ve kaynak kaydının korunması.
- Ingest tekrarları; 15 test kaydının tekrar yüklenmesinde çoğalmaması; rapor tutarı/satıcı izolasyonu; fonksiyonların PUBLIC erişiminin kapalı olması.
- Gazi sekmeleri/tablo başlıkları/detayları; 15 görsel fixture; paket editörü; telefon/WhatsApp; HTML kaçışları; tarayıcıdan tabloya doğrudan yazım olmaması.
- 14 Python testi: sandbox istek eşlemeleri ve mevcut gönderi kurtarma; başarısız sorguda yeni gönderi açmama; kaydedilmiş referans; olay sıralama; ortam ayrımı; COD; şifre; origin/CSRF; oturumsuz erişim; actor enjeksiyonu; kapalı ingest; statik güvenlik başlıkları.

Sınırlar: Tarayıcıda piksel/screenshot ve yazıcı testi yapılmadı. Docker ortamı başlatılmadı. Gerçek DHL hesabında yeni sandbox gönderisi bu teslimatta açılmadı. Cevap taklitleri ve mock kargolar gerçek DHL gönderisi olarak sunulmaz. Canlı veri aktarımı ve yayına geçiş yapılmadı.
