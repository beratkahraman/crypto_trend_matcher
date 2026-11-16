# 🚀 Binance AI Pattern Trader

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Binance API](https://img.shields.io/badge/Binance-API-yellow)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)

Bu bot, Binance Spot piyasasında **Görüntü İşleme / Patern Eşleştirme (DTW)** algoritmalarını kullanarak potansiyel yükseliş sinyallerini yakalayan ve yöneten otomatik bir alım-satım sistemidir.

Klasik indikatörlerin ötesine geçerek, **"Tarih tekerrürden ibarettir"** mantığıyla; o an yükselmekte olan (Top Gainers) coinlerin grafik şablonlarını analiz eder ve markette henüz yükselmemiş ama aynı formasyonu oluşturan "Aday Coinleri" tespit eder.

## 🔥 Temel Özellikler

* **🧠 Akıllı Tarama (Pattern Matching):** `FastDTW` kullanarak, yükselen coinlerin grafik karakteristiğini (imzasını) çıkarır ve benzer yapıdaki ucuz coinleri arar.
* **🛡️ Gelişmiş Risk Yönetimi (Risk Watcher):** Sabit stop-loss yerine, ATR tabanlı dinamik stop ve **Trailing Stop (İzleyen Stop)** mekanizması kullanır. Kar oranı arttıkça stop seviyesini yukarı çeker.
* **📉 Fake-Out Koruması:** Sadece grafiğe bakmaz; **RSI**, **Hacim Akışı (OBV)** ve **EMA50 Trend** analizleri ile sinyali doğrular.
* **📱 Telegram Entegrasyonu:** Alım/Satım işlemlerini, analiz grafiklerini (`.png`) ve günlük performans raporlarını cebinize gönderir. Telegram üzerinden `SAT` veya `RAPOR` gibi komutlarla botu yönetebilirsiniz.
* **💾 Veri Kaydı:** Tüm işlemleri SQLite veritabanında tutar ve geriye dönük performans analizi yapmanızı sağlar.

---

## ⚙️ Nasıl Çalışır?

Bot 3 ana modülden oluşur:

1.  **Scanner (Tarayıcı):**
    * Binance "Top Gainers" listesinden son 24 saatin yıldızlarını bulur.
    * Bu coinlerin yükseliş öncesi grafik şablonunu kopyalar.
    * Tüm marketi tarayarak bu şablona `%80+` benzerlik gösteren, henüz patlamamış coinleri bulur.
    * RSI < 70 ve Hacim onayı varsa sinyal üretir.

2.  **Validator (Doğrulayıcı):**
    * Bakiye kontrolü, "Soğuma Süresi (Cooldown)" ve maksimum işlem sayısı kontrollerini yapar.
    * Binance API üzerinden emri iletir.

3.  **Watcher (İzleyici):**
    * Açık işlemleri saniye saniye takip eder.
    * Fiyat yükseldikçe stop seviyesini yukarı taşır (Trailing Stop).
    * Ani düşüşlerde veya hedefe ulaşıldığında işlemi kapatır.

---

## 🛠️ Kurulum

Projeyi yerel makinenize veya sunucunuza (AWS/VPS) kurmak için adımları izleyin.

### 1. Gereksinimler
* Python 3.8 veya üzeri
* Binance Hesabı (API Key & Secret)
* Telegram Bot Token (Bildirimler için)

### 2. İndirme ve Yükleme

```bash
# Repoyu klonlayın
git clone https://github.com/beratkahraman/crypto_trend_matcher.git
cd crypto_trend_matcher

# Sanal ortam oluşturun (Önerilen)
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate

# Kütüphaneleri yükleyin
pip install -r requirements.txt
```
### 3.Konfigürasyon (.env)
Proje ana dizininde .env adında bir dosya oluşturun ve aşağıdaki bilgileri doldurun. Bu dosyayı asla kimseyle paylaşmayın!
```bash
# Binance API Bilgileri (Spot Alım/Satım yetkisi olmalı)
BINANCE_API_KEY=senin_api_keyin
BINANCE_API_SECRET=senin_secret_keyin

# Telegram Ayarları (BotFather'dan alınan)
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```
## ▶️ Kullanım
Botu başlatmak için ana dizinde terminali açın:
```bash
python main.py
```
Bot başladığında:

1. `bot.log` dosyasına sistem kayıtlarını atar.

2. Telegram'dan "Bot Başlatıldı" mesajı gönderir.

3. Periyodik olarak tarama yapar ve `data/plots/` klasörüne eşleşen grafiklerin görsellerini kaydeder.

### 🤖 Telegram Komutları
Bot çalışırken Telegram üzerinden şu komutları verebilirsiniz:

* RAPOR : Anlık cüzdan durumu, açık işlemler ve toplam kar/zarar raporunu gönderir.

* LOG : Sunucudaki bot.log dosyasını sohbet penceresine gönderir.

* SAT BTC : BTCUSDT paritesindeki işlemi (varsa) anında piyasa fiyatından satar.

## ⚠️ Yasal Uyarı (Disclaimer)
Bu yazılım deneysel amaçlı geliştirilmiş bir açık kaynak projesidir. Yatırım tavsiyesi değildir.

* Kripto para piyasaları yüksek risk içerir.

* Botun geçmiş performansı, gelecekteki sonuçları garanti etmez.

* Yazılımın kullanımı sonucu oluşabilecek maddi kayıplardan geliştirici sorumlu tutulamaz.

* Lütfen API anahtarlarınızı güvende tutun ve sadece güvendiğiniz sunucularda çalıştırın.
