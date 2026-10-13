# Gazi Sipariş

Gazi panelinin sipariş ve kargo süreçlerini kullanan PL/pgSQL uygulaması.

## Canlı panel

https://gazi-plpgsql-panel.brainyfrog33.chatgpt.site

DHL işlemleri için panelde **DHL Oturumu Aç** düğmesini kullanıp mevcut Gazi e-posta ve şifrenizle giriş yapın. Kargolama, etiket, hareket, iptal, bağlantı ve adres kodu işlemleri mevcut Gazi workflowlarına iletilir. Workflowların oturum doğrulaması korunur.

## Dosyalar

- Repo kökündeki `index.html` panelin girişidir. Görsel önizleme için `?demo=1` kullanın; canlı işlemler çalışan API gerektirir.
- `web/` bağımsız Docker uygulamasının arayüzüdür.
- Kurulum ve yapılandırma için `docs/`, veritabanı değişiklikleri için `database/` dizinlerine bakın.

## Arayüz

Sipariş detayının bilgi bölümü kaydırılır; ana işlem butonları sabit kalır. Hareket geçmişi okla açılan kapalı bir bölümdür. Liste satırları sıklaştırılmış ve müşteri isimleri koyulaştırılmıştır.

## Doğrulama

DOM, arama, durum butonları, oturum doğrulaması, eşzamanlı işlem engeli ve paket kontrolleri geçti. Gerçek ücretli gönderi veya iptal testi yapılmadı. Bu ortamda tarayıcıyla görsel doğrulama yapılamadı.

