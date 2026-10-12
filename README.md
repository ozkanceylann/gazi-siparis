# Gazi Sipariş — PL/pgSQL

Gazi ana panelinin sekmeleri, tabloları ve detay ekranları esas alınarak yazılan yeni sistem. Görünüm kaynağı `ozkanceylann/gazi`; mobil `siparis-takip` tasarımı kullanılmadı. Sipariş ve kargo iş kuralları sıfırdan `database/001_install.sql` içindeki PL/pgSQL fonksiyonlarında çalışır. Tarayıcı tabloları doğrudan değiştirmez.

## Canlı panel

https://gazi-plpgsql-panel.brainyfrog33.chatgpt.site

Aynı ChatGPT hesabınızla açın. Panel sahibine özel erişimle çalışır. Canlı `gazi_live` şemasında 2.480 gerçek sipariş ve 4.415.999 TL kaynak toplamı doğrulandı. 15 simülasyon siparişi ayrı `gazi_ops` şemasında kalır.

Sipariş ekleme, düzenleme, hazırlama ve mevcut DHL kargolarının gerçek hareket takibi kullanılabilir. Kaynak `public.gazi_siparisler` ile PL/pgSQL tetikleyicileri üzerinden çift yönlü senkronizasyon vardır. Yeni siparişler ortak `tum_siparisler` sipariş numarası ile açılır. Eski repo korunur.

**Gerçek DHL gönderisi oluşturma, yeni barkod/etiket kesme ve taşıyıcıda iptal yetkileri kapalıdır.** Bu işlemler için açık onay bekleniyor; hem arayüz hem servis ve gateway engelleri uygulanır. Mevcut kaydedilmiş etiketler okunabilir. Otomatik takip 30 dakika aralıklıdır. DHL hesap bağlantısı ve gerçek bir kargonun altı hareketinin kaydı doğrulandı.

Hosted sürüm Sites Worker → gizli servis anahtarı → Supabase Edge Function → PL/pgSQL kullanır. Anahtarlar tarayıcıya veya GitHub'a gönderilmez. Canlı geçiş SQL dosyaları `010`–`014`, runtime `gazi-live-runtime`, n8n gateway `n8n/live-gateway.sdk.ts` içindedir. Gateway kişisel Özkan CEYLAN n8n projesinde `GAZI_PLPGSQL_CANLI_GATEWAY` adıyla çalışır ve taşıyıcı sorgularını sınırlar.

Aşağıdaki Docker kurulumu bağımsız veritabanı/test kurulumu içindir; barındırılan canlı panel farklı `gazi_live` bağlantısını kullanır.

## Kurulum

Docker ve Docker Compose gereklidir.

```bash
cp .env.example .env
# .env içindeki DB_PASSWORD değerini güçlü, URL-safe bir parolayla değiştirin.
docker compose up -d --build
docker compose exec api python -m app.create_user --phone 05XXXXXXXXX --name "Gazi Yönetici" --role admin
```

Şifre terminalde gizli olarak sorulur. Ardından `http://localhost:8000` adresinde bu telefon/şifreyle giriş yapın. Eski Supabase girişleri yeni veritabanında otomatik oluşturulmaz.

Üretimde API'yi HTTPS reverse proxy arkasına koyun; `.env` içindeki `APP_ORIGIN` tam site adresi, `COOKIE_SECURE=true` olmalı. Veritabanının dışarı açık portu yoktur. `DATABASE_URL` yalnızca sunucuda bulunur. `gazi_ops` şeması bu kurulumun kendi PostgreSQL veritabanındadır; mevcut Gazi tabloları kullanılmaz.

## 15 test siparişi

```bash
docker compose exec -T db psql -U gazi -d gazi < database/003_test_seed.sql
```

Bu kayıtlar sentetiktir, **gerçek DHL gönderileri değildir**. Başlangıç modu `CARRIER_MODE=mock`: kargolama, paket barkodları, hareketler ve iptal simüle edilir. Görünümü kurulum olmadan incelemek için `web/index.html?demo=1` dosyasını statik sunucuda açabilirsiniz; demo işlemleri veritabanına yazmaz.

Akış: Bekleyen → Hazırla + hazırlama etiketi → Hazırlandı → Kargola + paket etiketleri → Kargolandı → Tamamlananlar / Sorunlu / İade. İptal, geri alma ve iptal kaydını listeden kaldırma ayrıca desteklenir.

## DHL sandbox

`.env` içinde `CARRIER_MODE=sandbox`, DHL test hesabının `DHL_CLIENT_ID`, `DHL_CLIENT_SECRET`, `DHL_CUSTOMER_NUMBER`, `DHL_PASSWORD` değerlerini ayarlayın; API ve worker'ı yeniden başlatın. Yeni bir test siparişi oluşturun. Mock gönderileri sandbox'a taşınmaz.

Adaptör `https://testapi.mngkargo.com.tr/mngapi/api/` adresini kullanır. IP izin listesi gerekirse normalize edilmiş HTTPS gateway kullanılabilir; sözleşme [docs/CARRIER.md](docs/CARRIER.md) içinde. Canlı doğrudan DHL URL'si varsayılmadı; canlı kullanım için doğrulanmış gateway ve `LIVE_CARGO_ENABLED=true` gerekir.

DHL'nin resmî ZPL etiketleri paket bazında kaydedilir. PDF dönüşümü için `LABELARY_ENABLED=true` seçeneği vardır; bu seçenek etiket verisini Labelary'ye gönderir. Varsayılan kapalıdır. PDF yoksa resmî ZPL indirilebilir; taşıyıcı özet ekranı resmî etiket yerine yazdırılmaz. Mock etiketlerinde belirgin TEST ibaresi bulunur.

## Siparişler ve takip

- Bekleyen kayıtların müşteri/adres/ürün/tutar/ödeme/not/paket bilgileri düzenlenebilir. Satıcı sadece kendine ait bekleyen kaydı düzenler.
- Hazırlama ve kargolama yöneticidedir. Kargolama işi aynı sipariş için tekilleştirilir; servis cevabı gelmeden Kargolandı yapılmaz.
- Tekli ve toplu hareket sorguları aynı `track` işini ve `finish_job` fonksiyonunu kullanır. Toplu işlem yalnızca ekranda görünen sayfayla sınırlı değildir.
- DHL'den gelen referans kaydedilir ve sonraki sorguda kullanılır. Eski hareket, güncel durumu geriye düşürmez; teslim edilmiş sipariş yeniden yolda olmaz.
- Worker, aktif/geri gelen gönderileri en erken 30 dakikada bir otomatik sorgular. Etiket tekrar açma yeni gönderi oluşturmaz.
- Kargosu oluşmuş siparişin iptali DHL cevabından sonra tamamlanır. Geri alma eski kargo/etiketi arşivler ve yeni referans için deneme numarasını artırır.
- Çift kayıt inceleme: aynı satıcı ve müşteri telefonu, 24 saat, iki kayıt da bekleyen. Yeni kaydın bilgileri hedefe aktarılır; tutarlar toplanmaz. Kaynak kayıt/audit korunur.
- Raporlar İstanbul saatine göre başlangıç/bitiş, durum ve arama filtrelerini tüm veriye uygular. Toplamlar, günlük/durum dağılımı ve tüm sayfaları kapsayan Excel uyumlu CSV vardır.

## İl / ilçe ve sipariş girişi

Doğrulanmış şehir/ilçe kodlarını CSV olarak yeni veritabanına yükleyin:

```bash
# cities.csv: code,name ; districts.csv: code,city_code,name
docker compose cp cities.csv api:/tmp/cities.csv
docker compose cp districts.csv api:/tmp/districts.csv
docker compose exec api python -m app.import_references --cities /tmp/cities.csv --districts /tmp/districts.csv
# Ön kontrolün ardından aynı komuta --apply ekleyin.
```

Referanslar yüklüyse düzenleme ekranında şehir/ilçe seçimleri ve kodlar birlikte güncellenir. Referanslar yokken isimle giriş mümkündür; "Sor" işlemi eksik kod listesini açıkça bildirir.

WhatsApp/n8n sipariş girişini yeni `/api/ingest` adresine bağlamak için sunucuda `INGEST_TOKEN` tanımlayın. Örnek ve alanlar [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). Mevcut workflow'lar otomatik değiştirilmez. Opsiyonel WhatsApp tepkileri sunucu tarafındaki webhook üzerinden gönderilir.

## Doğrulama

```bash
python -m pip install -r requirements-dev.txt
npm ci
npm test
npm run check
```

Gerçek PL/pgSQL, PGlite/PostgreSQL üzerinde çalıştırılır. UI DOM testleri ve Python taşıyıcı/API güvenlik testleri bulunur. Sonuçlar ve doğrulama sınırları: [docs/VERIFICATION.md](docs/VERIFICATION.md). Hosted PostgreSQL üzerinde hazırlama/kargolama/etiket/takip/iptal/geri alma/rapor zinciri doğrulandı. Gerçek DHL hesabında gönderi açılmadı; Docker ortamı başlatılmadı.
