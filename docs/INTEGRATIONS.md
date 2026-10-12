# Sipariş girişi ve mevcut sistem bağlantıları

Bu proje kendi PostgreSQL veritabanına kurulmalıdır. Mevcut `tum_siparisler` veya `gazi_siparisler` tabloları değiştirilmez. Tarih farkına bakılmaksızın `source_order_no` eski ortak sipariş numarasını korur; yeni iç numara ayrı olabilir.

Satıcılar yeni kullanıcı tablosunda telefonlarıyla tanımlanır. n8n → yeni `/api/ingest`:

```json
{
 "source_order_no":9000,
 "source_message_id":"EXAMPLE-MESSAGE-ID",
 "siparis_tel":"05550002222",
 "ad_soyad":"TEST Müşteri",
 "musteri_tel":"05551112233",
 "adres":"Test Mahallesi Örnek Sokak No 10",
 "sehir":"İzmir","ilce":"Konak",
 "urun_bilgisi":"Siyah Gemlik Sele Zeytin · TEST",
 "toplam_tutar":1100,
 "odeme_sekli":"Kapıda ödeme",
 "notlar":"TEST",
 "packages":[{"kg":10,"desi":10}]
}
```

Header: `Authorization: Bearer <INGEST_TOKEN>`. Kaynak sipariş no veya mesaj kimliği zorunludur. Tekrar iletilen mesaj aynı siparişi döndürür; başka bir sipariş oluşturmaz. Aynı müşteriyle 24 saat içindeki farklı mesaj çift kayıt sorunu oluşturur; otomatik birleştirme yapılmaz. Yönetici iki bekleyen kaydı inceleyip birleştirir. Kargo oluşmuş kayıt birleştirilmez.

`WHATSAPP_REACTION_URL` ve `WHATSAPP_REACTION_TOKEN` tanımlanırsa `{siparis_no,emoji}` JSON'u sunucu tarafından HTTPS webhook'a gönderilir. Eski kaynak sipariş no varsa o kullanılır. Gönderilmeyen tepki, hazırlanmış/kargolanmış siparişi geri almaz.

**Geçiş kapsamı:** Canlı eski kayıtlar, eski kargolar, Supabase kullanıcıları ve workflow'lar bu repo kurulumu sırasında kendiliğinden aktarılmaz. Canlı geçiş öncesi kaynak sipariş/kargo/etiket haritası, satıcı eşleştirmeleri ve adet/tutar mutabakatı ayrıca yapılmalıdır. `ingest` yeni bekleyen sipariş girişidir; eski kargolanmış kayıtları buna bekleyen sipariş olarak göndermeyin.
