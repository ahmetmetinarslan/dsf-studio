# DSF Studio 1.0 — gerçek test ve teslim raporu

Tarih: 11 Ekim 2026. Bu rapor çalıştırılan testleri ve test kapsamının sınırlarını ayırır.

## Teslim

- Çalıştırılabilir uygulama: `dist/DSF-Studio/DSF-Studio.exe`.
- Taşınabilir dağıtım: `release/DSF-Studio-1.0.0-Windows-x64.zip`. ZIP'in tamamını açın; EXE'yi `_internal` klasöründen ayırmayın.
- Kaynak paketi: `release/DSF-Studio-1.0.0-Source.zip`.
- Örnek proje: `examples/Ornek_Haber.dsfproj`; 10 adet temsili haber kartı `examples/assets` içinde.
- Gerçek örnek video: `examples/Ornek_Haber_80sn.mp4`.
- Kullanım, geliştirme ve paketleme: `README.md`.
- Sürümler: `requirements.lock`, `BUILD_INFO.json`; paket özetleri: `release/SHA256.json`.
- Lisans metinleri ve bildirimler: hazır pakette `licenses`, `THIRD_PARTY_NOTICES.md`.

Uygulama Python ve FFmpeg kurulumu gerektirmeyen bir klasör paketi olarak üretildi. Son kullanıcı EXE'yi çift tıklayarak açar. Kaynak klasörde `Baslat.cmd` de aynı paketi açar.

## Test ortamı

Windows 11 Pro x64, sürüm 10.0.26200 / build 26200. Intel Core i7-9750H, 6 çekirdek / 12 iş parçacığı; 16 GB RAM. Çalışma ve çıktı diski E:, SATA WDC WD10SPZX 1 TB HDD. Sistemde ayrıca Kingston 240 GB SSD var. Python 3.13.5, PySide6 6.9.2, Pillow 11.3.0, FFmpeg/ffprobe 8.0 full build, PyInstaller 6.15.0.

Testler geliştirme bilgisayarında çalıştırıldı. Bazı video, arayüz ve paketleme testleri eşzamanlı yürüdü; süreler izole benchmark değildir. Başka bilgisayarlar için hız garantisi verilmez.

## Sonuçlar

**40 birim testi geçti.** Ayrıca gerçek FFmpeg dosyaları, QProcess iş kuyruğu, Windows arayüzü, QTest fare işlemleri ve paketli EXE test edildi.

| Test | Sonuç | Gerçek kontrol ve kapsam |
| --- | --- | --- |
| K01 | Geçti | 10 × 8 sn × 25 fps; tek 1920×1080 H.264 MP4; ffprobe ile **2000 kare, 80.000000 sn**; tam çözme başarılı. |
| K02 | Geçti | Altı hareket için ayrı 8 saniyelik gerçek videolar. İlk/son karelerde kırmızı sentetik işaretin yeri veya büyüklüğü ölçüldü. Kamera ve görüntü yönleri doğru. |
| K03 | Geçti | Pan için başlangıç büyütmesi; azami ölçek 1 olduğunda hareket yok. İşaretli sentetik görselin 200 karesinde kenar kapsamı denetlendi; yeni boş kenar bulunmadı. |
| K04 | Geçti | Kenara yakın korunan alan için %15 istek yaklaşık **%4,2205**'e azaltıldı. 200 çözülmüş karenin hepsinde işaretli dikdörtgen %5 güvenli pay içinde kaldı. |
| K05 | Geçti | Tam çerçeveyi kaplayan korunacak alanda sabit dahil bütün hareketler `invalid_region`. Güvensiz plan renderdan önce engellenir. |
| K06 | Geçti | Alan yoksa `unchecked_content`; koruma kapalıysa ayrıca açık kapalı durumu. İçerik korunduğu iddia edilmiyor. |
| K07 | Geçti | 25 fps: 200 kare/8 sn ve kesirli sürede 26 kare/1,04 sn. 50 fps: 51+61 = 112 kare/2,24 sn. Tam kare yuvarlaması ayrıca birim testinde. |
| K08 | Geçti | Altı hareketin tümünde 960×540 önizleme ve 1920×1080 çıktı; ilk, orta, son karelerde işaret sınırları karşılaştırıldı. 1080p karşılığı en büyük fark **2 piksel**. Ek 50 fps senaryosu da geçti. |
| K09 | Kısmen doğrulandı | 200 pan karesinde boş kenar ve geri sıçrama yok; ölçülen kare başına işaret merkezi adımı 0–2 px. Küçük yazı/çizgi örnekleri üretildi, Qt oynatması çalıştı. **1080p gerçek hızda insan gözüyle öznel titreme değerlendirmesi yapılmadı.** |
| K10 | Geçti | Kaydet/aç döngüsünde sıra, süreler, hareket planları, kilitler, odaklar ve alanlar aynı. Göreli yollar, atomik kayıt, bozuk/future şema koruması ve ayrı kurtarma kaydı test edildi. |
| K11 | Geçti | Otomatik dağıtım izinli kümeden seçiyor; kilitli klibin kaydı aynı kalıyor. Kayıt/açma ve önizleme anahtarı hesabı yeniden rastgele atama yapmıyor. |
| K12 | Geçti | Türkçe/boşluklu yollar, bozuk görselin ayrı hata alması, eksik kaynakta renderın durması; **348 karakter kaynak / 340 karakter çıktı yolu** üzerinden gerçek 25 karelik MP4. EXIF, alpha, yanlış oran, bozuk ICC ve küçük görsel uyarısı da test edildi. |
| K13 | Geçti; disk hatası simüle edildi | Gerçek render sırasında iptal; eski hedef baytları değişmedi, işe ait geçici klasör temizlendi. Boş disk alanı, hazırlık sırasında ENOSPC ve atomik taşıma sırasında ENOSPC enjekte edildi; eski hedef korundu. Fiziksel disk bilerek doldurulmadı. |
| K14 | Geçti | Arayüze 100 ayrı 1080p görsel eklendi. Ayrıca **100 × 1 sn**, 25 fps, 2500 karelik projenin tamamı render edildi ve çözüldü. Kuyruk 1 klip; görüntü önbelleği 8; bellek tüm video kareleriyle birikmiyor. |
| K15 | Kısmen doğrulandı | PyInstaller ile gerçek Windows EXE üretildi. PATH yalnızca Windows sistem klasörlerini içerirken; PYTHONHOME/PYTHONPATH boşken paketli EXE, kendi FFmpeg/ffprobe araçlarıyla MP4 üretti ve Qt'de video kareleri oynattı. **Ayrı temiz Windows cihazı/VM mevcut değildi.** |
| K16 | Geçti; sentetik referans | Gerçek sRGB → BT.709 transfer ve matris/aralık dönüşümü. Gri rampada en fazla 2/255, toplam 64 gri/kırmızı/yeşil/mavi referansta en fazla **3/255** sapma. BT.709 etiketleri, limited range, yuv420p ve progressive doğrulandı. Profesyonel kalibre yayın monitöründe ölçüm yapılmadı. |
| K17 | Geçti | ffprobe tek video akışı ve ses yok sonucunu verdi. Render yolu kılavuz/alan/odak/sayaç çizmez; bağımsız temiz referans karelerle karşılaştırma yapıldı. |
| K18 | Geçti | 2000 zaman damgası tam 0,04 sn adımlı. 10 klibin ilk/son toplam 20 karesi bağımsız üretilen uç karelerle karşılaştırıldı; en büyük kanal başına ortalama piksel hatası 1,3899/255. Son kare 1999 mevcut; ek siyah veya yinelenmiş geçiş karesi bulunmadı. |

Geometri testleri iki eğriyi, asimetrik profilleri, 2 piksel iç payı, olanaksız/sabit/azaltılmış durumları ve sabit seed ile 600 rastgele alanı kapsadı. Orijinal görseller değiştirilmedi.

## Performans ve arayüz ölçümleri

| Ölçüm | Sonuç |
| --- | --- |
| 10 × 8 sn, 2000 kare, 1080p, CRF18 medium, 2× ara geometri | 255,330 sn; uygulama + alt süreçler tepe bellek 587,4 MiB |
| 100 × 1 sn, 2500 kare, aynı çıktı ayarları | 481,658 sn; uygulama + alt süreçler tepe bellek 344,7 MiB |
| 100 görselin gerçek arayüze eklenmesi | 86,292 sn; Python/Qt süreç tepe belleği 307,18 MiB |
| 100 görsellik arayüz testi sırasında en uzun ölçülen olay döngüsü aralığı | 1,446 sn |
| 100 görsellik tam render sırasında olay döngüsü en uzun aralığı | 0,129 sn |
| Gerçek render iptali | Çekirdek iş testinde 0,142 sn; Windows arayüz testinde 0,745 sn |

Arayüzde toplu süre uygulama, yukarı/aşağı sıralama, çoğaltma, kilit, yeniden dağıtım, geri al/yinele, fareyle dikdörtgen çizme, kurtarma, bozuk dosyanın ayrılması ve Qt oynatıcısının gerçek kare sunması çalıştırıldı. Son sürümde hareket yönü animasyonu ve dosya uzantısının farklı, onaylanmamış bir hedefe dönüşmemesi ayrıca test edildi.

## Kanıt dosyaları ve tekrar çalıştırma

- `artifacts/stage1/results.json`: altı gerçek video, yön ve kenar sonuçları.
- `artifacts/acceptance/K01_ffprobe.json`: 80 saniyelik dosyanın gerçek akış/format bilgileri.
- `artifacts/acceptance/results.json`: birleşik çıktı, kesmeler, güvenlik, fps, iptal ve renk sonuçları.
- `artifacts/acceptance/preview_six.json`: altı hareket için 18 önizleme/çıktı karşılaştırması.
- `artifacts/acceptance/color_reference.json`: 64 renk referansı.
- `artifacts/acceptance/stress100.json`: 100 görsellik tamamlanmış render ve bellek ölçümü.
- `artifacts/acceptance/extra.json`: uzun yol ve işlem sırasındaki disk hatası enjeksiyonları.
- `artifacts/gui/results.json`: gerçek arayüz ve oynatma testleri.
- `artifacts/package-check/package-check.json`: paketli EXE'nin gerçek MP4/Qt kontrolü.
- `artifacts/hardware.json`: test bilgisayarı.

Komutlar `README.md` içinde. Ek kontroller: `scripts/preview_six.py`, `scripts/color_reference.py`, `scripts/stress100.py`, `scripts/extra_checks.py`, `scripts/ui_quick.py`. Kanıt JSON'larının dağıtım kopyaları depoda, kaynak ZIP'inde ve Windows paketinde `test-evidence` klasöründedir. Bu kopyalarda makineye özel çalışma alanı yolu `<workspace>` ile değiştirilir; ölçümler değiştirilmez. Orijinal ham dosyalar geliştirme bilgisayarındaki `artifacts` klasöründe korunur.

## Kalan doğrulamalar

Temiz Windows kurulumu, Windows 10, profesyonel yayın monitörü ve belirli kanal teslim profili doğrulanmadı. K09'un insan tarafından gerçek hızda görüntü kalitesi değerlendirmesi açık kaldı. Gerçek haber fotoğrafları kullanıcı tarafından verilmediği için örnekler temsili kartlar ve sentetik test görüntüleridir. Bu maddeler tamamlanmış test olarak sayılmadı.

EXE dijital olarak imzalanmadı. Dağıtım, bütün bağımlılıkları içeren taşınabilir klasördür; kurulum sihirbazı değildir. Harici yeniden dağıtım için üçüncü taraf kaynak kodu sağlama koşulları hakkında `THIRD_PARTY_NOTICES.md` içindeki durum korunmuştur.
