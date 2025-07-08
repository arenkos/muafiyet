# Doğuş Üniversitesi OBS Ders İçerikleri PDF İndirme Scripti
## Ubuntu Sunucu Kurulum ve Çalıştırma Talimatları

Bu script, Doğuş Üniversitesi OBS sisteminden ders içeriklerini otomatik olarak PDF formatında indirir.

## 🚀 Özellikler

- ✅ Headless modda çalışır (GUI gerektirmez)
- ✅ Hem normal hem gruplu dersleri indirir
- ✅ Detaylı loglama sistemi
- ✅ Hata yönetimi ve otomatik kurtarma
- ✅ PDF dosya isimlerinde Türkçe karakter desteği

## 📋 Sistem Gereksinimleri

### Ubuntu 20.04/22.04 LTS
- Python 3.8+
- Chrome/Chromium browser
- ChromeDriver

## 🔧 Kurulum Adımları

### 1. Sistem Paketlerini Güncelle
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Python ve Gerekli Paketleri Kur
```bash
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y chromium-browser chromium-chromedriver
```

### 3. Chrome Bağımlılıklarını Kur
```bash
sudo apt install -y libnss3 libatk1.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libatspi2.0-0 libcups2 libdrm2 libgtk-3-0 libxss1 libxshmfence1 libxinerama1 libpango-1.0-0 libxext6 libxfixes3 libxrender1 libxtst6 fonts-liberation libappindicator3-1 libdbusmenu-glib4 libdbusmenu-gtk3-4 libindicator3-7
```

### 4. Proje Klasörünü Oluştur
```bash
mkdir -p ~/muafiyet
cd ~/muafiyet
```

### 5. Python Sanal Ortam Oluştur
```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. Python Bağımlılıklarını Kur
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Playwright Tarayıcılarını Kur
```bash
playwright install
```

## 🚀 Çalıştırma

### 1. Sanal Ortamı Aktifleştir
```bash
cd ~/muafiyet
source venv/bin/activate
```

### 2. Scripti Çalıştır
```bash
python3 icerik_indir_ubuntu.py
```

### 3. Arka Planda Çalıştırma (Opsiyonel)
```bash
nohup python3 icerik_indir_ubuntu.py > output.log 2>&1 &
```

## 📁 Çıktı Dosyaları

Script çalıştıktan sonra aşağıdaki dosyalar oluşur:

- `icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği/` - PDF dosyaları
- `muafiyet_indir.log` - Detaylı log dosyası

## 📊 Log Dosyası

Log dosyası şu bilgileri içerir:
- İşlem başlangıç/bitiş zamanları
- Bulunan ders sayısı
- Her dersin işlenme durumu
- Hata mesajları
- Toplam süre

## 🔧 Konfigürasyon

Script başında aşağıdaki değişkenleri düzenleyebilirsiniz:

```python
url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
pdf_klasoru = "icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
```

## 🛠️ Sorun Giderme

### Chrome Driver Hatası
```bash
# ChromeDriver'ı manuel kur
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f 3 | cut -d '.' -f 1)
wget https://chromedriver.storage.googleapis.com/$CHROME_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

### Playwright Hatası
```bash
# Playwright'ı yeniden kur
playwright install --force
```

### Bağımlılık Hatası
```bash
# Eksik paketleri kur
sudo apt install -y libgconf-2-4 libnss3-1d libxss1
```

## 📝 Cron Job ile Otomatik Çalıştırma

Günlük otomatik çalıştırma için:

```bash
# Cron job ekle
crontab -e

# Aşağıdaki satırı ekle (her gün saat 02:00'de çalışır)
0 2 * * * cd /home/kullanici/muafiyet && /home/kullanici/muafiyet/venv/bin/python3 /home/kullanici/muafiyet/icerik_indir_ubuntu.py
```

## 🔒 Güvenlik Notları

- Script headless modda çalışır, GUI gerektirmez
- Tüm işlemler loglanır
- Hata durumunda otomatik kurtarma mekanizması vardır

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Log dosyasını kontrol edin: `cat muafiyet_indir.log`
2. Sistem kaynaklarını kontrol edin: `htop`, `df -h`
3. Chrome sürümünü kontrol edin: `google-chrome --version`

## 📋 Sistem Gereksinimleri Kontrolü

```bash
# Python sürümü
python3 --version

# Chrome sürümü
google-chrome --version

# ChromeDriver sürümü
chromedriver --version

# Disk alanı
df -h

# RAM kullanımı
free -h
```

## 🎯 Performans İpuçları

- En az 2GB RAM önerilir
- SSD disk tercih edilir
- İnternet bağlantısı stabil olmalı
- Sunucu CPU kullanımı %80'in altında olmalı 