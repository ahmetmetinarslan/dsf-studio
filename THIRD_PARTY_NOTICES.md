# Üçüncü taraf bileşenler

DSF Studio 1.0; Python 3.13.5, PySide6/Qt 6.9.2, Pillow 11.3.0 ve FFmpeg/ffprobe 8.0 kullanır.
Tam Python paket listesi `requirements.lock`, derleme seçenekleri ve EXE SHA-256 özetleri `BUILD_INFO.json` içindedir.

- Python: PSF lisansı, https://docs.python.org/3/license.html
- PySide6, Shiboken ve kullanılan Qt modülleri: ilgili LGPL/GPL veya ticari lisans koşulları. Paket içindeki `licenses` klasöründe dağıtımla gelen metinler bulunur. Qt DLL'leri `_internal/PySide6` içinde ayrı dosyalardır.
- Pillow: HPND ve dağıtımın içerdiği bağımlılık bildirimleri; `licenses/Pillow`.
- PyInstaller: GPL ve uygulama paketleme istisnası; paketleme aracıdır.
- FFmpeg 8.0 Gyan full build: GPL sürüm 3 veya sonrası. `libx264` dahil etkin bileşenlerin listesi `BUILD_INFO.json` içindedir. FFmpeg ayrı süreç olarak çalışır; bu, dağıtım koşullarını kaldırmaz.

FFmpeg ikili dağıtım kaynağı:
https://github.com/GyanD/codexffmpeg/releases/tag/8.0

FFmpeg kaynak ağacı:
https://github.com/FFmpeg/FFmpeg/tree/n8.0

Dağıtıcının derleme ve kaynak bilgileri:
https://www.gyan.dev/ffmpeg/builds/
https://github.com/GyanD/codexffmpeg

Qt/PySide kaynakları:
https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.9.2
https://download.qt.io/archive/qt/6.9/6.9.2/

Bu klasör kişisel kullanım için hazırlanan taşınabilir derlemedir. Harici yeniden dağıtımda, tam derleme ve bütün GPL bileşenleri için karşılık gelen kaynak kodu sağlama yükümlülükleri ayrıca tamamlanmalıdır. Yalnızca yukarıdaki bağlantıların bulunması bütün yükümlülüklerin yerine getirildiği iddiası değildir.
