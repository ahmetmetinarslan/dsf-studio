# DSF Studio 1.0.0

Haber görsellerine yavaş zoom/pan hareketleri uygulayan, korunacak alanları gözeterek tek 1920×1080 MP4 oluşturan Türkçe Windows masaüstü uygulamasının ilk sürümü.

## İndir ve çalıştır

1. Aşağıdaki **Assets** bölümünden **DSF-Studio-1.0.0-Windows-x64.zip** dosyasını indirin.
2. ZIP'in tamamını bir klasöre çıkarın.
3. `DSF-Studio/DSF-Studio.exe` dosyasını açın. Python veya FFmpeg kurulumu gerekmez.
4. **Aç** ile `examples/Ornek_Haber.dsfproj` örneğini deneyin.

Klasördeki `_internal` dizinini EXE ile birlikte tutun. GitHub'ın **Source code** arşivleri hazır uygulama değildir. Bu özel depoya ve indirmelere erişmek için GitHub hesabınızla giriş yapın.

## İçerik

- Altı hareket, doğrusal/yumuşak eğri, odak ve birden fazla korunacak alan.
- Güvenli alanlara göre hareket miktarını azaltma ve açık durum bildirimi.
- Sıralama, toplu düzenleme, kilitleme, geri al/yinele ve otomatik kurtarma.
- Gerçek video önizlemesi ve 25/50 fps, H.264, BT.709, sessiz MP4 çıktısı.
- Örnek proje, 80 saniyelik örnek video, Türkçe README ve test raporu.

`DSF-Studio-1.0.0-Source.zip` geliştirme kaynaklarını, örnekleri ve test kanıtlarını içerir. `SHA256.json` dosyası iki ZIP'in bütünlük özetlerini verir.

## Doğrulama ve sınırlar

Windows 11 x64 üzerinde 40 birim testi; 2000 kare / 80 saniye video, altı hareket, güvenli alan, 25/50 fps, 100 görsellik render ve iptal testleri geçti. Paketli EXE kendi FFmpeg'iyle video oluşturup Qt'de oynattı.

Ayrı temiz Windows cihazı/VM ve Windows 10 testi yapılmadı. Gerçek hızda insan gözüyle titreme değerlendirmesi ve profesyonel yayın monitörü kontrolü açık. Disk dolması testleri hata enjeksiyonuyla yapıldı. EXE dijital imzalı değildir. Ayrıntılar depodaki `TEST_RESULTS.md` dosyasındadır.

Paket kişisel kullanım için özel depoda tutulur. Üçüncü taraf bileşenlerin bildirimleri ve harici yeniden dağıtım için kaynak sağlama durumu `THIRD_PARTY_NOTICES.md` içindedir.
