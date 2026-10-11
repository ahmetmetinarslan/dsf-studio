# DSF Studio — uygulama planı

1. Tek görsel: normalize medya, ortak dönüşüm, FFmpeg, altı yön, 200 kare.
2. Güvenlik: eşitsizlik çözücüsü, 2 px pay, azaltılmış/olanaksız/denetlenmemiş durumlar.
3. Masaüstü: PySide6, liste, toplu düzenleme, çizilebilir alanlar, önizleme, geri al.
4. Proje ve çıktı: sürümlü atomik JSON, kurtarma, yeniden bağlama, QProcess kuyruğu, iptal.
5. Dağıtım: sabit bağımlılıklar, taşınabilir Windows paketi, kabul testi kanıtları.

Varsayılan: 1920×1080, 25 fps, 8 s, H.264 CRF18 medium, sessiz, kesme.
Kullanıcının mevcut dosyaları değiştirilmeyecek. Temiz cihaz testi yapılmadıkça yapıldı denmeyecek.

## Gerçekleşen durum

- Tek görsel çekirdeği: altı yönde 200 karelik MP4 ve piksel testleri geçti.
- Güvenlik motoru: 40 toplam birim testinin geometri kısmı, 600 rastgele alan ve gerçek render sınır testi geçti.
- Masaüstü: Windows'ta açıldı; 100 görsel, çizim, toplu ayar, geri al, kilit ve Qt video oynatma testleri geçti.
- Proje ve birleşik çıktı: atomik kayıt/kurtarma, yeniden bağlama, 2000 kare/80 sn, iptal ve hata enjeksiyonu doğrulandı.
- Paket: gerçek Windows x64 EXE oluşturuldu; paketli araçlarla üretim ve oynatma çalıştı. Temiz ayrı cihaz ve insan gözüyle normal hız kalite kontrolü açık kaldı; ayrıntı TEST_RESULTS.md.
