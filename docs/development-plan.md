# Geliştirme planı ve doğrulama sınırları

## Bu düzenlemenin kapsamı

Mevcut kamera prototipi küçük modüllere ayrıldı. Kalibrasyon süresi (3.0), yükselme (0.055), hız (0.12), bekleme (0.65) ve dönüş (0.025) eşikleri korundu. Ekran metinleri, sayaç, görünürlük kontrolleri ve R/Q tuşları korunuyor.

Başlangıçtaki model yolu proje köküne bağlandı. Modül içe aktarılırken kamera açılmıyor. Model dosyası Git dışında kalıyor.

Donanımsız kontrollerin başarı durumu GitHub Actions üzerinden görülmelidir. Kamera ile davranış eşdeğerliği, MediaPipe/OpenCV kurulumu ve fiziksel radar çalışması bu testlerden çıkarılamaz.

## Kamerada elle karşılaştırma

Aynı model, kamera konumu, ışık, kişi ve çalışan Python ortamıyla önceki sürümle yeni dal karşılaştırılmalı:

1. Hareketsiz duruşta kalibrasyonun ve sayacın kontrolü.
2. Normal ve hafif zıplamalar.
3. Tek harekette çift sayım olmaması ve inişten sonra yeniden hazır olma.
4. Yavaş/hızlı parmak ucuna yükselme: mevcut yanlış pozitifler kaydedilmeli; çözülmüş sayılmamalı.
5. Omuz veya kalça görünürlüğünün kaybolup geri gelmesi.
6. R ile kalibrasyon/sayaç sıfırlama; Q ile çıkış ve kamera kaynağının bırakılması.

## Algılamayı iyileştirme

Önce zaman damgalı gövde konumu, görünürlük, hız, yükselme ve karar kaydı eklenmeli. Normal/hafif zıplama, parmak ucuna yükselme, çömelme, yürüme ve takip kaybı etiketlenmeli.

Sonra kararlı kalibrasyon, zaman tabanlı hız penceresi ve takip kaybından dönüş ayrı değişikliklerde ele alınmalı. Ayak bileği (27–28), topuk (29–30) ve ayak ucu (31–32) özellikleri aday doğrulamasında denenebilir. Görüntü koordinatları kesin zemin teması veya metrik zıplama yüksekliği sağlamaz. Ayaklar görünmediğinde belirsizlik ayrıca ele alınmalı.

Yeni yöntem mevcut yöntemle aynı kayıtlar üzerinde karşılaştırılmalı. Yanlış pozitif, kaçırılan hafif zıplama, çift sayım ve oyun kontrolünü etkileyen gecikme birlikte ölçülmeli.

## Radar için bağımsız modül

İlk hedef zıplama kararı değil, ham bayt kaydı ve protokol doğrulamasıdır:

- `radar/serial_reader.py`: Yapılandırılabilir port/baud/zaman aşımı ve bağlantı hataları. COM5 yerel bir ayardır.
- `radar/protocol.py`: Üretici belgesine göre tamponlama, çerçeve sınırları, alan kodlaması, birimler ve bozuk veriden toparlanma.
- `radar/recorder.py`: Ham baytlar ve monoton zaman damgaları.
- Çevrimdışı tekrar oynatma ve eksik/birleşik/bozuk paket testleri.

PySerial bağımlılığı bu modül geliştirilirken eklenmeli. Dönüştürücünün COM5 olarak tanınması radarın veri ürettiğini doğrulamaz. Elektriksel bağlantılar ve seri ayarlar donanım belgeleriyle doğrulanmadan güç verme adımı oluşturulmamalı.

LD2450 X/Y konumu ve hız alanları doğrudan dikey zıplama yüksekliği değildir. Montaj, koordinat sistemi, örnekleme davranışı ve gerçek hareket kayıtları incelenmeden radarın zıplamayı tek başına ayırabildiği varsayılmamalı.

## Unity ve sunucu

Radar veri çıkışı ve hareket özellikleri doğrulandıktan sonra Python–Unity olay sözleşmesi ve iletişim yöntemi tasarlanmalı. Kamera karşılaştırma/destek kaynağı olarak tutulmalı. ASP.NET Core Web API ve SQL Server altyapısı sonraki aşamadır.
