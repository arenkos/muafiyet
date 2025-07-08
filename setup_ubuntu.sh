#!/bin/bash

# Doğuş Üniversitesi OBS Ders İçerikleri PDF İndirme Scripti
# Ubuntu Sunucu Otomatik Kurulum Scripti

set -e  # Hata durumunda scripti durdur

echo "🚀 Doğuş Üniversitesi OBS PDF İndirme Scripti - Ubuntu Kurulumu"
echo "================================================================"

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log fonksiyonu
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Root kontrolü
if [[ $EUID -eq 0 ]]; then
   error "Bu script root kullanıcısı ile çalıştırılmamalıdır!"
   exit 1
fi

# Sistem güncellemesi
log "Sistem paketleri güncelleniyor..."
sudo apt update && sudo apt upgrade -y

# Gerekli sistem paketlerini kur
log "Gerekli sistem paketleri kuruluyor..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    chromium-browser \
    chromium-chromedriver \
    wget \
    unzip \
    curl \
    git

# Chrome bağımlılıklarını kur
log "Chrome bağımlılıkları kuruluyor..."
sudo apt install -y \
    libnss3 \
    libatk1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3-0 \
    libxss1 \
    libxshmfence1 \
    libxinerama1 \
    libpango-1.0-0 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libdbusmenu-glib4 \
    libdbusmenu-gtk3-4 \
    libindicator3-7

# Proje klasörünü oluştur
log "Proje klasörü oluşturuluyor..."
mkdir -p ~/muafiyet
cd ~/muafiyet

# Python sanal ortam oluştur
log "Python sanal ortam oluşturuluyor..."
python3 -m venv venv

# Sanal ortamı aktifleştir
log "Sanal ortam aktifleştiriliyor..."
source venv/bin/activate

# pip'i güncelle
log "pip güncelleniyor..."
pip install --upgrade pip

# Python bağımlılıklarını kur
log "Python bağımlılıkları kuruluyor..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    warn "requirements.txt bulunamadı, temel paketler kuruluyor..."
    pip install selenium playwright webdriver-manager requests
fi

# Playwright tarayıcılarını kur
log "Playwright tarayıcıları kuruluyor..."
playwright install

# ChromeDriver kontrolü
log "ChromeDriver kontrol ediliyor..."
if ! command -v chromedriver &> /dev/null; then
    warn "ChromeDriver bulunamadı, manuel kurulum yapılıyor..."
    
    # Chrome sürümünü al
    CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f 3 | cut -d '.' -f 1)
    log "Chrome sürümü: $CHROME_VERSION"
    
    # ChromeDriver indir
    wget -O chromedriver.zip "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
    LATEST_VERSION=$(cat chromedriver.zip)
    wget -O chromedriver.zip "https://chromedriver.storage.googleapis.com/$LATEST_VERSION/chromedriver_linux64.zip"
    
    # ChromeDriver'ı kur
    unzip chromedriver.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    
    # Temizlik
    rm -f chromedriver.zip
fi

# Test scripti oluştur
log "Test scripti oluşturuluyor..."
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
import sys
import subprocess

def test_imports():
    try:
        import selenium
        print("✅ Selenium kuruldu")
    except ImportError:
        print("❌ Selenium kurulamadı")
        return False
    
    try:
        import playwright
        print("✅ Playwright kuruldu")
    except ImportError:
        print("❌ Playwright kurulamadı")
        return False
    
    return True

def test_chrome():
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Chrome kuruldu: {result.stdout.strip()}")
            return True
        else:
            print("❌ Chrome bulunamadı")
            return False
    except Exception as e:
        print(f"❌ Chrome test hatası: {e}")
        return False

def test_chromedriver():
    try:
        result = subprocess.run(['chromedriver', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ChromeDriver kuruldu: {result.stdout.strip()}")
            return True
        else:
            print("❌ ChromeDriver bulunamadı")
            return False
    except Exception as e:
        print(f"❌ ChromeDriver test hatası: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Sistem testleri yapılıyor...")
    print("=" * 40)
    
    success = True
    success &= test_imports()
    success &= test_chrome()
    success &= test_chromedriver()
    
    print("=" * 40)
    if success:
        print("✅ Tüm testler başarılı! Sistem kullanıma hazır.")
    else:
        print("❌ Bazı testler başarısız. Lütfen hataları kontrol edin.")
        sys.exit(1)
EOF

# Test scriptini çalıştır
log "Sistem testleri yapılıyor..."
python3 test_setup.py

# Başarı mesajı
echo ""
echo "🎉 Kurulum tamamlandı!"
echo "========================"
echo "📁 Proje klasörü: ~/muafiyet"
echo "🐍 Sanal ortam: ~/muafiyet/venv"
echo "📝 Log dosyası: ~/muafiyet/muafiyet_indir.log"
echo ""
echo "🚀 Scripti çalıştırmak için:"
echo "cd ~/muafiyet"
echo "source venv/bin/activate"
echo "python3 icerik_indir_ubuntu.py"
echo ""
echo "📖 Detaylı bilgi için: cat README_UBUNTU.md"
echo ""

# Cron job önerisi
read -p "Cron job ile otomatik çalıştırma eklemek ister misiniz? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Cron job ekleniyor..."
    (crontab -l 2>/dev/null; echo "0 2 * * * cd /home/$USER/muafiyet && /home/$USER/muafiyet/venv/bin/python3 /home/$USER/muafiyet/icerik_indir_ubuntu.py") | crontab -
    log "Cron job eklendi! Script her gün saat 02:00'de çalışacak."
fi

log "Kurulum başarıyla tamamlandı!" 