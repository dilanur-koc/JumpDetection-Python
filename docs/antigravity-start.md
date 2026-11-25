# Antigravity ile çalışma — 6 Kasım 2026

Bu dosya tarihli çalışma notudur. Güncel oynanabilir kamera gösterimi, fizik değerleri ve
dosya haritası için [25 Kasım rehberini](2026-11-25-demo-guide.md) kullanın.

## Açılacak klasör

Antigravity'de projeye şu kök klasörü ekleyin:
`C:\Users\Dila\Documents\JumpDetectionTest`.
Yalnız Unity alt klasörünü açmak Python ve API bağlamını eksik bırakabilir.

`GEMINI.md` ortak proje yönergelerini içerir. `.agents/agents/` içinde
`radar-reviewer`, `unity-reviewer`, `backend-reviewer` tanımları vardır.
Bunlar dosya okuma/arama araçları olan inceleme ajanlarıdır; komut veya dosya
yazma aracı verilmemiştir. Yönergeler uygulamanın izin mekanizmasının yerine geçmez.
Tanım eklemek ajanı çalıştırmak anlamına gelmez; bu hazırlıkta ajan başlatılmadı.

Google'ın güncel belgelerinde özel alt ajanlar Antigravity App/CLI için
belgelenmiştir. Kurulu IDE sürümü bunları göstermiyorsa rastgele eklenti kurmayın:
aynı görev metnini normal ajan sohbetinde kullanın. Antigravity App/CLI'da
`/agents` üzerinden tanımların bulunup bulunmadığını kontrol edin.

## İlk görev metni

```text
GEMINI.md ve docs/antigravity-start.md dosyalarını oku. Önce git status ve
mevcut farkları kontrol et; dosya değiştirme. Destekliyorsan radar-reviewer
ile unity-reviewer ajanlarına kendi kapsamlarında salt okunur inceleme ver.
Aynı dosyaya paralel değişiklik yaptırma. Hedef kaybı, radar adayı, UDP
gönderimi, Unity kabulü ve fiziksel zıplama uygulamasını ayrı değerlendir.
Kanıtları ve önerdiğin en küçük sonraki adımı Türkçe anlat.
Masaüstü/seri port/SQL kontrolü için ayrıca ilgili kapsamda izin iste.
```

API görevi olduğunda ayrıca `backend-reviewer` kullanılabilir.

## Bugünkü doğrulanmış durum

- Çalışma ağacında yerel değişiklikler var; bunlar bu hazırlıkta yayınlanmadı.
- `JumpPrototype.cs`: varsayılan ilerleme hızı 3.5; zıplama ilk hızı 11.5;
  yerçekimi çarpanı 2.5. Engel X konumları 11, 16, 21, 26.
- Radar/simülasyon modunda üç saniyelik geri sayımdan sonra ilk geçerli
  zıplama uygulanana kadar yatay ilerleme bekletilir. İlk uygulanan zıplama
  tur süresini ve otomatik hareketi başlatır.
- Debug panelinde ham UDP, kabul sayısı, zıplama durumu ve tur/zemin durumu
  ayrı gösterilir. Kontrollü tek simülasyon denemesinde Raw UDP 1,
  Accepted 1, Jumps 1 ve Jump applied gözlendi. Bu, radar doğruluğunu ölçmez.
- Kullanıcı sonraki donanım denemesinde 6 zıplamadan 1'inin sayıldığını bildirdi.
  Yerel `recordings/radar/20261106_104741_908293_trial.summary.json`
  bir aday ve bir UDP gönderimi içeriyor. UDP gönderimi alıcı onayı değildir.
- Aynı kayıtta yaklaşık 13.984–20.578 saniyeler arasında hedef görünmüyor;
  sonrasında yeniden kalibrasyon var. Daha önce uzun hareket adayı iptali de var.
  Gerçek radar olayının bu denemede Unity'de uygulandığı ayrıca doğrulanmadı.
- Kullanıcı aynı noktada, yaklaşık 1–2 metre uzakta zıplıyor; radar klavyenin
  üzerine yatık konuyor. Montaj yüksekliği henüz bilinmiyor. Yatık yerleşimin
  kayba katkısı olabilir; neden olduğu henüz kontrollü deneyle kanıtlanmadı.
- Sonraki deneyde sensörü sabit, dik ve anten yüzü kullanıcıya dönük yerleştirip
  hedef görünürlüğünü karşılaştırın. Üreticinin duvara montaj önerisi 1.5–2 m'dir;
  bu öneri zıplama algılaması için doğruluk garantisi değildir.

Antigravity hazırlığından sonraki kullanıcı isteğiyle radar hareket hız eşiği
16'dan 12 cm/sn'ye, düzlemsel yer değiştirme 60'tan 30 mm'ye indirildi.
Yeni kayıt sürümü `burst-quiet-v3-sensitive`; örnek/süre/takip kontrolleri korunur.
Pencere başarılı UDP gönderim sayısını anlık gösterir; alıcı onayı değildir.
Bu hassasiyetin gerçek zıplamadaki başarımı henüz ölçülmedi; yürüyüşte yanlış
sayımı artırabilir. Hedef kaybında eksik ölçümü geri getirmez.
11:31 denemesi 2 aday ve 2 gönderim içeriyor; gerçek zıplama sayısı girilmemiş.
Bu denemede 47 aktif karede birden fazla hedef durumu var. Eski CSV'yi eski
16/60 ve yeni 12/30 eşikleriyle çevrimdışı karşılaştırma her ikisinde de aynı
iki adayı üretti (12.921 ve 31.234 s). Yeni eşikler bu kayıttaki kaçırmaları
gidermedi; canlı başarı artışı gösterilmedi. Python değişikliklerinden sonra
77 test geçti; donanımın doğru zıplama saydığını bu testler kanıtlamaz.
Sonraki Unity kontrolünde Play kapalıydı; bu durum eski denemenin alıcı
durumunu kanıtlamaz. Test için Play yeniden açıldı.

## Kaynaklar

- [Google: proje kuralları](https://antigravity.google/docs/rules/)
- [Google: özel alt ajanlar ve Markdown tanımları](https://antigravity.google/docs/subagents/)
- [Hi-Link LD2450 kılavuzu, montaj bölümü](https://h.hlktech.com/download/HLK-LD2450-24G/1/HLK%20LD2450%201T2R%E8%BF%90%E5%8A%A8%E7%9B%AE%E6%A0%87%E6%A3%80%E6%B5%8B%E8%BF%BD%E8%B8%AA%E6%A8%A1%E7%BB%84%E8%AF%B4%E6%98%8E%E4%B9%A6%20V1.02%20.pdf)
