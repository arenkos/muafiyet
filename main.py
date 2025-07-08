from PyPDF2 import PdfReader
import re
import spacy
import os
# Gemini API için gerekli import
import google.generativeai as genai
import zipfile
import shutil
import time
from pathlib import Path
import unicodedata

# GEMINI API AYARI
# (Kullanıcıdan gelen anahtar ile ayarlanıyor)
genai.configure(api_key="AIzaSyBd_xFTGutOOL4K4EdbwwK3zV-V3MJxrWg")

# Cache için global değişken
pdf_cache = {}
ders_icerik_cache = {}

def normalize_string(s):
    """Türkçe karakterleri normalize eder ve büyük/küçük harf duyarlılığını kaldırır"""
    # Önce küçük harfe çevir
    s = s.lower()
    
    # Türkçe karakterleri manuel olarak değiştir
    turkish_chars = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
    }
    
    for turkish_char, replacement in turkish_chars.items():
        s = s.replace(turkish_char, replacement)
    
    # Sonra Unicode normalize et
    normalized = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii')
    return normalized

def get_cached_pdf_content(file_path):
    """PDF içeriğini cache'den al veya oku"""
    if file_path in pdf_cache:
        return pdf_cache[file_path]
    
    try:
        pdf_reader = PdfReader(file_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        pdf_cache[file_path] = text
        return text
    except Exception as e:
        print(f"PDF okuma hatası: {str(e)}")
        return ""

# Transkriptteki geçilen dersleri sıralıyor ve out.txt dosyasına yazıyor
def process_pdf_content(pdf_content, derece):
    """
    Transkriptteki başarılı dersleri işler ve output.txt dosyasına yazar
    
    Args:
        pdf_content (str): PDF içeriği
        derece (str): Öğrenim derecesi (Önlisans/Lisans)
    """
    lines = pdf_content.split('\n')
    output_lines = []
    
    # Her satırı kontrol et
    for i in range(len(lines) - 2):
        line1 = lines[i]
        line2 = lines[i+1]
        line3 = lines[i+2]

        # Yıldız işaretlerini temizle
        if line1.startswith('*'):
            line1 = line1.lstrip('*')

        # İlk format kontrolü - ders bilgileri 2 satırda
        match = re.match(r'(\w+\s\d+)\s(.+)', line1)
        match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line2)

        if match and match2:
            course_code = match.group(1)
            course_name = match.group(2).replace('\t', ' ')
            akts = match2.group(6)
            grade = int(match2.group(7)) / int(akts)
            
            # Sadece başarılı dersleri ekle (not 0'dan büyük veya G notu)
            if int(match2.group(7)) != 0 or line2.endswith("G"):
                output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

        # İkinci format kontrolü - ders bilgileri 3 satırda
        match = re.match(r'(\w+\s\d+)\s(.+)', line1)
        match_ = re.match(r'(.+)', line2)
        match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line3)

        if match and match_ and match2:
            course_code = match.group(1)
            course_name = f"{match.group(2)} {match_.group(1)}".replace('\t', ' ')
            akts = match2.group(6)
            grade = int(match2.group(7)) / int(akts)
            
            if int(match2.group(7)) != 0 or line2.endswith("G"):
                output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

    # Sonuçları dosyaya yaz
    with open("output.txt", "w", encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + "\n")

# Tekrar eden satırları kaldırıyor
def remove_duplicate_lines(input_file, output_file):
    unique_lines = set()

    # Metin dosyasını oku ve her bir satırı küme veri yapısına ekle
    with open(input_file, 'r') as f:
        for line in f:
            unique_lines.add(line.strip())

    # Eşsiz satırları içeren bir liste oluştur
    unique_lines_list = list(unique_lines)

    # Yeni dosyaya eşsiz satırları yaz
    with open(output_file, 'w') as f:
        for line in unique_lines_list:
            f.write(line + '\n')

# Gemini API ile benzerlik hesaplama fonksiyonu
def gemini_similarity(text1, text2):
    """
    Gemini API ile iki metin arasındaki benzerlik oranını döndürür.
    text1: str
    text2: str
    return: float (0-1 arası benzerlik oranı)
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        Aşağıda iki ders içeriği metni var. Lütfen bu iki metnin içerik olarak yüzde kaç benzer olduğunu (0-100 arası bir sayı ile, sadece sayıyı) belirt:
        1. {text1}
        2. {text2}
        Sadece sayıyı döndür.
        """
        response = model.generate_content(prompt)
        # Yanıttan sadece sayı kısmını çek
        similarity_str = response.text.strip().split("\n")[0]
        similarity = float(similarity_str)
        # 0-100 arası değeri 0-1 arası değere çevir
        return similarity / 100.0
    except Exception as e:
        print(f"Gemini API benzerlik hatası: {str(e)}")
        return 0.0

# Ders içerik dosyasındaki haftaları ders_icerik.txt dosyasına yazma
def process_ders_icerik_dogus(pdf_content):
    lines = pdf_content.split('\n')
    output_lines = []

    for i in range(len(lines) - 16):
        line1 = lines[i]
        line2 = lines[i + 1]

        if line1 == "Ders Konuları" and line2 == "Hafta Konu Ön Hazırlık Dökümanlar":
            hafta = []
            hafta.append(lines[i + 2])
            hafta.append(lines[i + 3])
            hafta.append(lines[i + 4])
            hafta.append(lines[i + 5])
            hafta.append(lines[i + 6])
            hafta.append(lines[i + 7])
            hafta.append(lines[i + 8])
            hafta.append(lines[i + 9])
            hafta.append(lines[i + 10])
            hafta.append(lines[i + 11])
            hafta.append(lines[i + 12])
            hafta.append(lines[i + 13])
            hafta.append(lines[i + 14])
            hafta.append(lines[i + 15])
            say = 0
            for say in range(len(hafta)):
                match = re.match(r'(\d+)\s(\-\s\-)(.*)', hafta[say])

                if match:
                    hafta_sayisi = match.group(1)
                    ders_icerigi = match.group(3)
                    if ders_icerigi[0] == ' ':
                        ders_icerigi = ders_icerigi[1:]

                    output_lines.append(f"{'Hafta ' + hafta_sayisi}\t{ders_icerigi}")


    with open("ders_icerik.txt", "w") as f:
        for line in output_lines:
            f.write(line + "\n")
    # print("Tablo başarıyla oluşturuldu ve 'output.txt' dosyasına yazıldı.")
    icerik = []
    for a in range(len(output_lines)):
        m = re.match(r'(\w+\s\d+)\t(.*)', output_lines[a])
        icerik.append(m.group(1) + '\t' + m.group(2))
    return icerik

# Ders içeriği PDF dosyasını çekme
def ders_icerik_al(ders_kod_al):
    """
    Ders içeriği PDF dosyasını okur ve içeriği döndürür
    
    Args:
        ders_kod_al (str): Ders kodu
        
    Returns:
        list: Ders içeriği haftalık konular listesi
    """
    try:
        pdf_file = f'{ders_kod_al}.pdf'
        
        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"{pdf_file} bulunamadı")
            
        pdf_reader = PdfReader(pdf_file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text()
            
        return process_ders_icerik_dogus(text)
        
    except Exception as e:
        print(f"Hata: {str(e)}")
        return []

# Muafiyet hesaplanmasını yönetmeliğe göre yaparak muaf_olunan_dersler.txt dosyasına yazar
def muafiyet_hesapla(similarity_threshold=0.7):
    """
    Muafiyet kriterlerine göre dersleri karşılaştırır ve sonuçları dosyaya yazar
    
    Args:
        similarity_threshold (float): Minimum benzerlik oranı (0-1 arası)
    """
    muaf_olunan_dersler = []
    
    for kaynak_ders in zip(ders_kod_kaynak, ders_ad_kaynak, ders_akts_kaynak, ders_zs_kaynak):
        for hedef_ders in zip(ders_kod, ders_ad, ders_akts, ders_not):
            try:
                if (kaynak_ders[0] == hedef_ders[0] and 
                    float(kaynak_ders[2]) >= float(hedef_ders[2])):
                    muaf_olunan_dersler.append(
                        f"{kaynak_ders[0]} {kaynak_ders[1]}\t{kaynak_ders[2]}\t{kaynak_ders[3]}\t-->\t"
                        f"{hedef_ders[0]} {hedef_ders[1]}\t{hedef_ders[2]}\t{hedef_ders[3]}"
                    )
                    break
                    
                # Diğer kontroller...
                
            except Exception as e:
                print(f"Hata oluştu: {str(e)}")
                continue

    with open("muaf_olunan_dersler.txt", "w", encoding='utf-8') as f:
        for line in muaf_olunan_dersler:
            f.write(line + "\n")


class MuafiyetSistemi:
    def __init__(self, use_gemini=False):
        """Sınıfın başlangıç değerlerini ayarlar"""
        self.nlp = spacy.load("en_core_web_md")
        self.ders_kod = []
        self.ders_ad = []
        self.ders_akts = []
        self.ders_not = []
        self.ders_kod_kaynak = []
        self.ders_ad_kaynak = []
        self.ders_akts_kaynak = []
        self.ders_zs_kaynak = []
        self.use_gemini = use_gemini
        
    def process_pdf_content(self, pdf_content, derece):
        """Transkript içeriğini işler"""
        lines = pdf_content.split('\n')
        output_lines = []
        
        for i in range(len(lines) - 2):
            line1 = lines[i]
            line2 = lines[i+1]
            line3 = lines[i+2]

            # Yıldız işaretlerini temizle
            if line1.startswith('*'):
                line1 = line1.lstrip('*')

            # İlk format kontrolü - ders bilgileri 2 satırda
            match = re.match(r'(\w+\s\d+)\s(.+)', line1)
            match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line2)

            if match and match2:
                course_code = match.group(1)
                course_name = match.group(2).replace('\t', ' ')
                akts = match2.group(6)
                grade = int(match2.group(7)) / int(akts)
                
                # Sadece başarılı dersleri ekle (not 0'dan büyük veya G notu)
                if int(match2.group(7)) != 0 or line2.endswith("G"):
                    output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

            # İkinci format kontrolü - ders bilgileri 3 satırda
            match = re.match(r'(\w+\s\d+)\s(.+)', line1)
            match_ = re.match(r'(.+)', line2)
            match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line3)

            if match and match_ and match2:
                course_code = match.group(1)
                course_name = f"{match.group(2)} {match_.group(1)}".replace('\t', ' ')
                akts = match2.group(6)
                grade = int(match2.group(7)) / int(akts)
                
                if int(match2.group(7)) != 0 or line2.endswith("G"):
                    output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

        # Sonuçları dosyaya yaz
        with open("output.txt", "w", encoding='utf-8') as f:
            for line in output_lines:
                f.write(line + "\n")

    def _parse_mufredat(self, text_lines):
        """Müfredat dosyasını parse eder"""
        for line in text_lines:
            m = re.match(r'(\w+\s\d+)\s(.*)\s(\d+)\s(.*)\s(\w+)', line)
            if m:
                self.ders_kod_kaynak.append(m.group(1))
                self.ders_ad_kaynak.append(m.group(4))
                self.ders_akts_kaynak.append(m.group(3))
                self.ders_zs_kaynak.append(m.group(5))

    def _add_muaf_ders(self, muaf_list, kaynak_index, hedef_index):
        """Muaf olan dersi listeye ekler"""
        muaf_list.append(
            f"{self.ders_kod_kaynak[kaynak_index]} {self.ders_ad_kaynak[kaynak_index]}\t"
            f"{self.ders_akts_kaynak[kaynak_index]}\t{self.ders_zs_kaynak[kaynak_index]}\t-->\t"
            f"{self.ders_kod[hedef_index]} {self.ders_ad[hedef_index]}\t"
            f"{self.ders_akts[hedef_index]}\t{self.ders_not[hedef_index]}"
        )

    def check_similarity(self, text1, text2):
        """Ders isimleri için özel benzerlik hesaplama algoritması"""
        if self.use_gemini:
            return gemini_similarity(text1, text2)
        else:
            return self._calculate_course_similarity(text1, text2)
    
    def _calculate_course_similarity(self, text1, text2):
        """
        Ders isimleri için özel benzerlik hesaplama
        - Kelime bazlı karşılaştırma
        - Anahtar kelime ağırlıkları
        - Sıralama önemli
        """
        # Metinleri normalize et
        text1 = self._normalize_course_name(text1)
        text2 = self._normalize_course_name(text2)
        
        # Tam eşleşme kontrolü
        if text1 == text2:
            return 1.0
        
        # Kelimeleri ayır
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Boş kelime listesi
        stop_words = {
            've', 'ile', 'için', 'giriş', 'temel', 'ilkeleri', 'yönetimi', 
            'sistemleri', 'teknolojisi', 'mühendisliği', 'bilimi', 'teorisi',
            'uygulaması', 'analizi', 'tasarımı', 'geliştirme', 'programlama',
            'işletim', 'veritabanı', 'ağ', 'web', 'mobil', 'yapay', 'zeka',
            'güvenlik', 'ağ', 'sistem', 'yazılım', 'donanım', 'bilgisayar'
        }
        
        # Stop words'leri çıkar
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        # Boş kümeler kontrolü
        if not words1 or not words2:
            return 0.0
        
        # Jaccard benzerliği
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # Anahtar kelime ağırlıkları
        key_words1 = self._extract_key_words(text1)
        key_words2 = self._extract_key_words(text2)
        
        key_word_similarity = 0.0
        if key_words1 and key_words2:
            key_intersection = len(set(key_words1).intersection(set(key_words2)))
            key_union = len(set(key_words1).union(set(key_words2)))
            if key_union > 0:
                key_word_similarity = key_intersection / key_union
        
        # N-gram benzerliği (2-gram)
        bigram_similarity = self._calculate_ngram_similarity(text1, text2, 2)
        
        # Kısmi eşleşme kontrolü (bir ders ismi diğerinin içinde mi?)
        partial_match = 0.0
        if len(text1) > len(text2):
            if text2.lower() in text1.lower():
                partial_match = 0.8
        else:
            if text1.lower() in text2.lower():
                partial_match = 0.8
        
        # Ağırlıklı ortalama
        final_similarity = (
            jaccard_similarity * 0.3 +
            key_word_similarity * 0.3 +
            bigram_similarity * 0.2 +
            partial_match * 0.2
        )
        
        return min(final_similarity, 1.0)
    
    def _normalize_course_name(self, text):
        """Ders ismini normalize eder"""
        # Türkçe karakterleri normalize et
        text = normalize_string(text)
        
        # Gereksiz karakterleri temizle
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_key_words(self, text):
        """Ders isminden anahtar kelimeleri çıkarır"""
        # Önemli ders türleri
        course_types = {
            'programlama', 'algoritma', 'veritabanı', 'ağ', 'web', 'mobil',
            'yapay', 'zeka', 'güvenlik', 'sistem', 'yazılım', 'donanım',
            'matematik', 'fizik', 'kimya', 'biyoloji', 'ekonomi', 'işletme',
            'muhasebe', 'pazarlama', 'yönetim', 'organizasyon', 'insan',
            'kaynakları', 'strateji', 'finans', 'bankacılık', 'sigorta',
            'turizm', 'otel', 'restoran', 'mutfak', 'aşçılık', 'gastronomi',
            'mimarlık', 'tasarım', 'grafik', 'görsel', 'iletişim', 'medya',
            'psikoloji', 'sosyoloji', 'felsefe', 'tarih', 'coğrafya',
            'edebiyat', 'dil', 'çeviri', 'mütercim', 'tercüman', 'hukuk',
            'adalet', 'siyaset', 'kamu', 'yönetimi', 'uluslararası', 'ilişkiler',
            'mühendislik', 'elektrik', 'elektronik', 'makine', 'endüstri',
            'inşaat', 'çevre', 'enerji', 'nükleer', 'petrol', 'maden',
            'tekstil', 'moda', 'tasarım', 'iç', 'mekan', 'dış', 'mekan',
            'sağlık', 'tıp', 'hemşirelik', 'eczacılık', 'diş', 'veteriner',
            'tarım', 'orman', 'su', 'ürünleri', 'gıda', 'teknik', 'eğitim'
        }
        
        words = text.lower().split()
        key_words = [word for word in words if word in course_types]
        
        return key_words
    
    def _calculate_ngram_similarity(self, text1, text2, n):
        """N-gram benzerliği hesaplar"""
        def get_ngrams(text, n):
            words = text.lower().split()
            ngrams = []
            for i in range(len(words) - n + 1):
                ngrams.append(' '.join(words[i:i+n]))
            return set(ngrams)
        
        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return intersection / union if union > 0 else 0.0

    def ders_icerik_al(self, ders_kodu):
        """Ders içeriğini okur (cache ile optimize edilmiş)"""
        try:
            # Cache kontrolü
            if ders_kodu in ders_icerik_cache:
                return ders_icerik_cache[ders_kodu]
            
            # Boşlukları kaldır ve sayı ile harf arasına boşluk ekle
            ders_kodu = re.sub(r'\s+', '', ders_kodu)  # Tüm boşlukları kaldır
            ders_kodu = re.sub(r'(\w)(\d+)', r'\1 \2', ders_kodu)  # Sayı ve harf arasına boşluk ekle
            if '\t' in ders_kodu:
                ders_kodu.lstrip('\t')
            
            # Yeni dosya yapısına göre ders içerik dosyasını bul
            if hasattr(self, 'icerikler_klasoru'):
                # Case-insensitive dosya arama
                pdf_file = self.find_case_insensitive_file(self.icerikler_klasoru, f'{ders_kodu}.pdf')
                print(f"DEBUG: İçerik dosyası aranıyor: {pdf_file}")
            else:
                # Eski yapı için geriye dönük uyumluluk
                pdf_file = f'{ders_kodu}.pdf'
                print(f"DEBUG: İçerikler klasörü yok, eski yapı kullanılıyor: {pdf_file}")
            
            self._check_file_exists(pdf_file)
            
            # Cache'den PDF içeriğini al
            text = get_cached_pdf_content(pdf_file)
            if not text:
                raise FileNotFoundError(f"PDF içeriği okunamadı: {pdf_file}")
            
            # İçeriği işle ve cache'e kaydet
            icerik = self.process_ders_icerik_dogus(text)
            ders_icerik_cache[ders_kodu] = icerik
            
            return icerik
            
        except Exception as e:
            print(f"Ders içeriği okuma hatası ({ders_kodu}): {str(e)}")
            return []

    def find_case_insensitive_file(self, parent_path, file_name):
        """Case-insensitive olarak dosya arar"""
        if not os.path.exists(parent_path):
            return os.path.join(parent_path, file_name)
        
        for item in os.listdir(parent_path):
            if os.path.isfile(os.path.join(parent_path, item)) and item.lower() == file_name.lower():
                return os.path.join(parent_path, item)
        
        # Eğer bulunamazsa, orijinal yolu döndür
        return os.path.join(parent_path, file_name)

    def process_ders_icerik_dogus(self, pdf_content):
        """Ders içeriğini işler"""
        lines = pdf_content.split('\n')
        output_lines = []

        for i in range(len(lines) - 16):
            line1 = lines[i]
            line2 = lines[i + 1]

            if line1 == "Ders Konuları" and line2 == "Hafta Konu Ön Hazırlık Dökümanlar":
                hafta = []
                hafta.append(lines[i + 2])
                hafta.append(lines[i + 3])
                hafta.append(lines[i + 4])
                hafta.append(lines[i + 5])
                hafta.append(lines[i + 6])
                hafta.append(lines[i + 7])
                hafta.append(lines[i + 8])
                hafta.append(lines[i + 9])
                hafta.append(lines[i + 10])
                hafta.append(lines[i + 11])
                hafta.append(lines[i + 12])
                hafta.append(lines[i + 13])
                hafta.append(lines[i + 14])
                hafta.append(lines[i + 15])
                say = 0
                for say in range(len(hafta)):
                    match = re.match(r'(\d+)\s(\-\s\-)(.*)', hafta[say])

                    if match:
                        hafta_sayisi = match.group(1)
                        ders_icerigi = match.group(3)
                        if ders_icerigi[0] == ' ':
                            ders_icerigi = ders_icerigi[1:]

                        output_lines.append(f"{'Hafta ' + hafta_sayisi}\t{ders_icerigi}")


        with open("ders_icerik.txt", "w") as f:
            for line in output_lines:
                f.write(line + "\n")
        # print("Tablo başarıyla oluşturuldu ve 'output.txt' dosyasına yazıldı.")
        icerik = []
        for a in range(len(output_lines)):
            m = re.match(r'(\w+\s\d+)\t(.*)', output_lines[a])
            icerik.append(m.group(1) + '\t' + m.group(2))
        return icerik

    def _check_file_exists(self, file_path):
        """Dosyanın varlığını kontrol eder"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} bulunamadı")

    def transkript_oku(self, transkript_paths):
        """Transkript PDF'lerini okur ve işler"""
        try:
            all_ders_kodlari = []
            all_ders_adlari = []
            all_ders_akts = []
            all_ders_notlar = []
            
            # Her transkript dosyasını işle
            for transkript_path in transkript_paths:
                print(f"  İşleniyor: {os.path.basename(transkript_path)}")
                
                self._check_file_exists(transkript_path)
                pdf_reader = PdfReader(transkript_path)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                    
                derece = "Önlisans" if "Akademik Derece Türü:Önlisans" in text else "Lisans"
                self.process_pdf_content(text, derece)
                
                # Dosyadan dersleri oku
                if os.path.exists("output.txt"):
                    with open("output.txt", "r", encoding='utf-8') as f:
                        ders_satirlari = f.readlines()
                    
                    # Her satırı parse et
                    for line in ders_satirlari:
                        line = line.strip()
                        if line:  # Boş satırları atla
                            match = re.match(r'(.*)\t(.*)\t(\d+)\t(.*)', line)
                            if match:
                                all_ders_kodlari.append(match.group(1))
                                all_ders_adlari.append(match.group(2))
                                all_ders_akts.append(match.group(3))
                                all_ders_notlar.append(match.group(4))
                
                # Geçici dosyayı temizle
                if os.path.exists("output.txt"):
                    os.remove("output.txt")
            
            # Tekrar eden dersleri kaldır (ders kodu bazında)
            unique_dersler = {}
            for i, ders_kodu in enumerate(all_ders_kodlari):
                if ders_kodu not in unique_dersler:
                    unique_dersler[ders_kodu] = {
                        'kod': ders_kodu,
                        'ad': all_ders_adlari[i],
                        'akts': all_ders_akts[i],
                        'not': all_ders_notlar[i]
                    }
            
            # Sonuçları sınıf değişkenlerine ata
            self.ders_kod = [d['kod'] for d in unique_dersler.values()]
            self.ders_ad = [d['ad'] for d in unique_dersler.values()]
            self.ders_akts = [d['akts'] for d in unique_dersler.values()]
            self.ders_not = [d['not'] for d in unique_dersler.values()]
            
            print(f"  Toplam {len(self.ders_kod)} benzersiz ders bulundu")
                    
        except Exception as e:
            print(f"Transkript okuma hatası: {str(e)}")
            raise

    def mufredat_oku(self, pdf_path):
        """Müfredat PDF'ini okur ve işler"""
        try:
            self._check_file_exists(pdf_path)
            pdf_reader = PdfReader(pdf_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
                
            self._parse_mufredat(text.split("\n"))
            
        except Exception as e:
            print(f"Müfredat okuma hatası: {str(e)}")

    def muafiyet_hesapla(self, similarity_threshold=0.7):
        """Muafiyet değerlendirmesi yapar"""
        muaf_olunan_dersler = []
        
        for i, kaynak_ders in enumerate(self.ders_kod_kaynak):
            for j, hedef_ders in enumerate(self.ders_kod):
                try:
                    # Ders kodu kontrolü
                    if (kaynak_ders == hedef_ders and 
                        float(self.ders_akts_kaynak[i]) >= float(self.ders_akts[j])):
                        self._add_muaf_ders(muaf_olunan_dersler, i, j)
                        break
                        
                    # Ders adı benzerliği kontrolü
                    elif (self.check_similarity(self.ders_ad_kaynak[i], self.ders_ad[j]) >= similarity_threshold and
                          float(self.ders_akts_kaynak[i]) >= float(self.ders_akts[j])):
                        
                        # Ders içeriği benzerliği kontrolü (opsiyonel)
                        try:
                            kaynak_icerik = self.ders_icerik_al(self.ders_kod_kaynak[i])
                            hedef_icerik = self.ders_icerik_al(self.ders_kod[j])
                            if not kaynak_icerik == [] and not hedef_icerik == []:
                                if self.check_similarity(" ".join(kaynak_icerik), " ".join(hedef_icerik)) >= similarity_threshold:
                                    self._add_muaf_ders(muaf_olunan_dersler, i, j)
                                    break
                        except:
                            # Ders içeriği bulunamazsa sadece ders adı benzerliğine göre karar ver
                            self._add_muaf_ders(muaf_olunan_dersler, i, j)
                            break
                            
                except Exception as e:
                    print(f"Muafiyet hesaplama hatası: {str(e)}")
                    continue

        # Sonuçları dosyaya yaz
        with open("muaf_olunan_dersler.txt", "w", encoding='utf-8') as f:
            for line in muaf_olunan_dersler:
                f.write(line + "\n")

def muafiyet_islem_baslat(zip_dosyasi, universite_adi, bolum_adi, use_gemini=False):
    """
    Muafiyet işlem sürecini başlatır
    
    Args:
        zip_dosyasi: Yüklenen ZIP dosyası
        universite_adi: Üniversite adı
        bolum_adi: Bölüm adı
        use_gemini: Gemini API kullanılıp kullanılmayacağı
    """
    print("=== MUAFİYET İŞLEM SÜRECİ BAŞLIYOR ===")
    baslangic_zamani = time.time()
    
    try:
        # 1. ZIP dosyasını extract et
        print("1. ZIP dosyası extract ediliyor...")
        extract_klasoru = "ogrenci_dosyalari"
        if os.path.exists(extract_klasoru):
            shutil.rmtree(extract_klasoru)
        os.makedirs(extract_klasoru)
        
        with zipfile.ZipFile(zip_dosyasi, 'r') as zip_ref:
            # Türkçe karakter desteği ile extract
            for file_info in zip_ref.infolist():
                try:
                    # Dosya adını UTF-8 ile decode et
                    filename = file_info.filename.encode('cp437').decode('utf-8')
                except:
                    # Fallback: orijinal adı kullan
                    filename = file_info.filename
                
                # Dosyayı extract et
                zip_ref.extract(file_info, extract_klasoru)
                
                # Dosya adını düzelt
                old_path = os.path.join(extract_klasoru, file_info.filename)
                new_path = os.path.join(extract_klasoru, filename)
                
                if old_path != new_path and os.path.exists(old_path):
                    # Klasör yapısını oluştur
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    # Dosyayı taşı
                    shutil.move(old_path, new_path)
        
        print("✓ ZIP dosyası başarıyla extract edildi")
        
        # 2. Transkript klasöründeki belgelerden başarılı dersleri topla
        print("2. Transkript belgeleri işleniyor...")
        transkript_klasoru = os.path.join(extract_klasoru, "transkript")
        if not os.path.exists(transkript_klasoru):
            # Alt klasörlerde transkript klasörünü ara
            for root, dirs, files in os.walk(extract_klasoru):
                for dir_name in dirs:
                    if dir_name.lower() == "transkript":
                        transkript_klasoru = os.path.join(root, dir_name)
                        break
                if os.path.exists(transkript_klasoru):
                    break
            
            if not os.path.exists(transkript_klasoru):
                raise FileNotFoundError("Transkript klasörü bulunamadı")
        
        transkript_dosyalari = []
        for dosya in os.listdir(transkript_klasoru):
            if dosya.endswith('.pdf'):
                transkript_dosyalari.append(os.path.join(transkript_klasoru, dosya))
        
        if not transkript_dosyalari:
            raise FileNotFoundError("Transkript PDF dosyası bulunamadı")
        
        print(f"Bulunan transkript dosyaları: {len(transkript_dosyalari)}")
        for dosya in transkript_dosyalari:
            print(f"  - {os.path.basename(dosya)}")
        
        # Muafiyet sistemi başlat
        muafiyet_sistemi = MuafiyetSistemi(use_gemini=use_gemini)
        
        # Tüm transkript dosyalarını tek seferde işle
        print(f"Transkript dosyaları işleniyor...")
        muafiyet_sistemi.transkript_oku(transkript_dosyalari)
        
        print(f"✓ {len(muafiyet_sistemi.ders_kod)} başarılı ders bulundu")
        
        # 3. Tekrar eden ders kodlarını kaldır
        print("3. Tekrar eden dersler temizleniyor...")
        unique_dersler = {}
        for i, ders_kodu in enumerate(muafiyet_sistemi.ders_kod):
            if ders_kodu not in unique_dersler:
                unique_dersler[ders_kodu] = {
                    'ad': muafiyet_sistemi.ders_ad[i],
                    'akts': muafiyet_sistemi.ders_akts[i],
                    'not': muafiyet_sistemi.ders_not[i],
                    'index': i
                }
        
        # Temizlenmiş listeleri güncelle
        muafiyet_sistemi.ders_kod = list(unique_dersler.keys())
        muafiyet_sistemi.ders_ad = [unique_dersler[k]['ad'] for k in unique_dersler.keys()]
        muafiyet_sistemi.ders_akts = [unique_dersler[k]['akts'] for k in unique_dersler.keys()]
        muafiyet_sistemi.ders_not = [unique_dersler[k]['not'] for k in unique_dersler.keys()]
        print(f"✓ {len(muafiyet_sistemi.ders_kod)} benzersiz ders kaldı")
        
        # 4. Müfredat dosyasını oku
        print("4. Müfredat dosyası işleniyor...")
        mufredat_klasoru = "mufredat"  # Ana dizindeki mufredat klasörü
        if not os.path.exists(mufredat_klasoru):
            raise FileNotFoundError("Müfredat klasörü bulunamadı")
        
        # Üniversite ve bölüm klasörlerini ara
        universite_klasoru = None
        for item in os.listdir(mufredat_klasoru):
            item_path = os.path.join(mufredat_klasoru, item)
            if os.path.isdir(item_path):
                # Normalize edilmiş isimleri karşılaştır
                normalized_search = normalize_string(universite_adi)
                normalized_item = normalize_string(item)
                if normalized_search in normalized_item or normalized_item in normalized_search:
                    universite_klasoru = item_path
                    break
        
        if not universite_klasoru:
            # Mevcut klasörleri listele
            available_folders = [item for item in os.listdir(mufredat_klasoru) 
                               if os.path.isdir(os.path.join(mufredat_klasoru, item))]
            raise FileNotFoundError(f"Üniversite klasörü bulunamadı: {universite_adi}. Mevcut klasörler: {available_folders}")
        
        # Bölüm dosyasını ara
        mufredat_dosyasi = None
        for item in os.listdir(universite_klasoru):
            if item.lower().endswith('.pdf'):
                # Normalize edilmiş isimleri karşılaştır
                normalized_search = normalize_string(bolum_adi)
                normalized_item = normalize_string(item.replace('.pdf', ''))
                if normalized_search in normalized_item or normalized_item in normalized_search:
                    mufredat_dosyasi = os.path.join(universite_klasoru, item)
                    break
        
        if not mufredat_dosyasi:
            # Mevcut dosyaları listele
            available_files = [item for item in os.listdir(universite_klasoru) 
                             if item.lower().endswith('.pdf')]
            raise FileNotFoundError(f"Müfredat dosyası bulunamadı: {universite_adi}/{bolum_adi}. Mevcut dosyalar: {available_files}")
        
        muafiyet_sistemi.mufredat_oku(mufredat_dosyasi)
        print(f"✓ {len(muafiyet_sistemi.ders_kod_kaynak)} müfredat dersi bulundu")
        
        # Müfredat derslerini mufredat.txt dosyasına yaz
        print("4a. Müfredat dersleri mufredat.txt dosyasına yazılıyor...")
        mufredat_yazildi = mufredat_derslerini_dosyaya_yaz(mufredat_dosyasi)
        if mufredat_yazildi:
            print("✓ Müfredat dersleri mufredat.txt dosyasına yazıldı")
        else:
            print("⚠️ Müfredat dersleri dosyaya yazılamadı")
        
        # 5. İçerikler klasörünü kontrol et
        icerikler_yolu = f"icerikler/{universite_adi}/{bolum_adi}"
        if not os.path.exists(icerikler_yolu):
            print(f"⚠️ İçerikler klasörü bulunamadı: {icerikler_yolu}")
            print("Ders içerikleri indiriliyor...")
            # Ders içeriklerini indir
            url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
            hibrit_pdf_indir(url, icerikler_yolu)
        
        # Muafiyet sistemine içerikler klasörünü ata
        muafiyet_sistemi.icerikler_klasoru = icerikler_yolu
        print(f"DEBUG: İçerikler klasörü atandı: {icerikler_yolu}")
        
        # 6. Muafiyet hesaplama süreci
        print("5. Muafiyet hesaplama süreci başlıyor...")
        muaf_olunan_dersler = []
        
        # 6a. Ders kodu eşleşmesi kontrolü
        print("5a. Ders kodu eşleşmesi kontrol ediliyor...")
        # Dosya isimlerini normalize ederek karşılaştır
        icerik_dosyalari = [f.replace('.pdf', '') for f in os.listdir(icerikler_yolu) if f.endswith('.pdf')]
        icerik_dosyalari_norm = [normalize_string(f) for f in icerik_dosyalari]
        
        print(f"DEBUG: İçerik dosyaları sayısı: {len(icerik_dosyalari)}")
        print(f"DEBUG: İlk 5 içerik dosyası: {icerik_dosyalari[:5]}")
        print(f"DEBUG: Öğrenci dersleri sayısı: {len(muafiyet_sistemi.ders_kod)}")
        print(f"DEBUG: İlk 5 öğrenci dersi: {muafiyet_sistemi.ders_kod[:5]}")
        
        for i, ders_kodu in enumerate(muafiyet_sistemi.ders_kod):
            ders_kodu_norm = normalize_string(ders_kodu)
            print(f"DEBUG: Kontrol ediliyor: {ders_kodu} -> {ders_kodu_norm}")
            
            if ders_kodu_norm in icerik_dosyalari_norm:
                idx = icerik_dosyalari_norm.index(ders_kodu_norm)
                dosya_adi = icerik_dosyalari[idx]
                print(f"✓ {ders_kodu} - Ders kodu eşleşmesi bulundu (dosya: {dosya_adi})")
                muaf_olunan_dersler.append({
                    'kaynak_ders': ders_kodu,
                    'hedef_ders': ders_kodu,
                    'benzerlik_tipi': 'ders_kodu_eslesmesi',
                    'benzerlik_orani': 1.0,
                    'akts_kontrol': True
                })
                print(f"DEBUG: Muaf listesine eklendi. Şu anki sayı: {len(muaf_olunan_dersler)}")
            else:
                print(f"⚠️ {ders_kodu} için içerik dosyası bulunamadı (devam ediliyor)")
                # En yakın eşleşmeleri göster
                for j, norm_dosya in enumerate(icerik_dosyalari_norm):
                    if ders_kodu_norm in norm_dosya or norm_dosya in ders_kodu_norm:
                        print(f"  DEBUG: Benzer dosya bulundu: {icerik_dosyalari[j]} -> {norm_dosya}")
        
        # 6b. Ders adı benzerliği kontrolü
        print("5b. Ders adı benzerliği kontrol ediliyor...")
        print(f"DEBUG: Ders adı kontrolü yapılacak ders sayısı: {len([d for d in muafiyet_sistemi.ders_kod if d not in [m['kaynak_ders'] for m in muaf_olunan_dersler]])}")
        
        for i, ders_kodu in enumerate(muafiyet_sistemi.ders_kod):
            if ders_kodu not in [m['kaynak_ders'] for m in muaf_olunan_dersler]:
                print(f"DEBUG: Ders adı kontrolü yapılıyor: {ders_kodu}")
                for j, hedef_ders_kodu in enumerate(muafiyet_sistemi.ders_kod_kaynak):
                    benzerlik = muafiyet_sistemi.check_similarity(
                        muafiyet_sistemi.ders_ad[i], 
                        muafiyet_sistemi.ders_ad_kaynak[j]
                    )
                    print(f"DEBUG: {ders_kodu} vs {hedef_ders_kodu} benzerlik: {benzerlik:.3f}")
                    if benzerlik >= 0.7:
                        print(f"✓ {ders_kodu} - {hedef_ders_kodu} ders adı benzerliği: {benzerlik:.2f}")
                        muaf_olunan_dersler.append({
                            'kaynak_ders': ders_kodu,
                            'hedef_ders': hedef_ders_kodu,
                            'benzerlik_tipi': 'ders_adi_benzerligi',
                            'benzerlik_orani': benzerlik,
                            'akts_kontrol': float(muafiyet_sistemi.ders_akts[i]) >= float(muafiyet_sistemi.ders_akts_kaynak[j])
                        })
                        print(f"DEBUG: Muaf listesine eklendi. Şu anki sayı: {len(muaf_olunan_dersler)}")
                        break
        
        # 6c. İçerik benzerliği kontrolü (sadece gerekli durumlarda)
        print("5c. İçerik benzerliği kontrol ediliyor...")
        icerik_kontrol_edilecek_dersler = []
        for i, ders_kodu in enumerate(muafiyet_sistemi.ders_kod):
            if ders_kodu not in [m['kaynak_ders'] for m in muaf_olunan_dersler]:
                icerik_kontrol_edilecek_dersler.append((i, ders_kodu))
        print(f"İçerik kontrolü yapılacak ders sayısı: {len(icerik_kontrol_edilecek_dersler)}")
        for i, ders_kodu in icerik_kontrol_edilecek_dersler:
            try:
                ogrenci_icerik = muafiyet_sistemi.ders_icerik_al(ders_kodu)
                if ogrenci_icerik:
                    for j, hedef_ders_kodu in enumerate(muafiyet_sistemi.ders_kod_kaynak):
                        try:
                            hedef_icerik = muafiyet_sistemi.ders_icerik_al(hedef_ders_kodu)
                            if hedef_icerik:
                                benzerlik = muafiyet_sistemi.check_similarity(
                                    " ".join(ogrenci_icerik), 
                                    " ".join(hedef_icerik)
                                )
                                if benzerlik >= 0.7:
                                    print(f"✓ {ders_kodu} - {hedef_ders_kodu} içerik benzerliği: {benzerlik:.2f}")
                                    muaf_olunan_dersler.append({
                                        'kaynak_ders': ders_kodu,
                                        'hedef_ders': hedef_ders_kodu,
                                        'benzerlik_tipi': 'icerik_benzerligi',
                                        'benzerlik_orani': benzerlik,
                                        'akts_kontrol': float(muafiyet_sistemi.ders_akts[i]) >= float(muafiyet_sistemi.ders_akts_kaynak[j])
                                    })
                                    break
                        except Exception as e:
                            print(f"⚠️ {hedef_ders_kodu} içerik okuma hatası: {str(e)} (devam ediliyor)")
                            continue
            except Exception as e:
                print(f"⚠️ {ders_kodu} içerik okuma hatası: {str(e)} (devam ediliyor)")
                continue
        
        # 7. Sonuçları dosyaya yaz
        print("6. Sonuçlar kaydediliyor...")
        print(f"DEBUG: Muaf olunan ders sayısı: {len(muaf_olunan_dersler)}")
        print(f"DEBUG: Muaf olunan dersler: {muaf_olunan_dersler}")
        
        with open("muaf_olunan_dersler.txt", "w", encoding='utf-8') as f:
            f.write("MUAF OLUNAN DERSLER\n")
            f.write("=" * 50 + "\n\n")
            
            if not muaf_olunan_dersler:
                f.write("Hiç muaf olunan ders bulunamadı.\n")
                print("DEBUG: Muaf olunan ders listesi boş!")
            else:
                for muaf_ders in muaf_olunan_dersler:
                    print(f"DEBUG: İşleniyor muaf ders: {muaf_ders}")
                    try:
                        kaynak_index = muafiyet_sistemi.ders_kod.index(muaf_ders['kaynak_ders'])
                        print(f"DEBUG: Kaynak index bulundu: {kaynak_index}")
                    except Exception as e:
                        print(f"⚠️ Kaynak ders listede yok: {muaf_ders['kaynak_ders']} (devam ediliyor)")
                        print(f"DEBUG: Mevcut kaynak dersler: {muafiyet_sistemi.ders_kod}")
                        continue
                    try:
                        hedef_index = muafiyet_sistemi.ders_kod_kaynak.index(muaf_ders['hedef_ders'])
                        print(f"DEBUG: Hedef index bulundu: {hedef_index}")
                    except Exception as e:
                        print(f"⚠️ Hedef ders listede yok: {muaf_ders['hedef_ders']} (devam ediliyor)")
                        print(f"DEBUG: Mevcut hedef dersler: {muafiyet_sistemi.ders_kod_kaynak}")
                        continue
                    
                    f.write(f"Kaynak Ders: {muaf_ders['kaynak_ders']} - {muafiyet_sistemi.ders_ad[kaynak_index]}\n")
                    f.write(f"Hedef Ders: {muaf_ders['hedef_ders']} - {muafiyet_sistemi.ders_ad_kaynak[hedef_index]}\n")
                    f.write(f"Benzerlik Tipi: {muaf_ders['benzerlik_tipi']}\n")
                    f.write(f"Benzerlik Oranı: {muaf_ders['benzerlik_orani']:.2f}\n")
                    f.write(f"AKTS Kontrolü: {'✓' if muaf_ders['akts_kontrol'] else '✗'}\n")
                    f.write("-" * 30 + "\n\n")
                    print(f"DEBUG: Ders yazıldı: {muaf_ders['kaynak_ders']}")
        
        # 8. İstatistikler
        bitis_zamani = time.time()
        sure = bitis_zamani - baslangic_zamani
        
        print(f"\n=== MUAFİYET İŞLEMİ TAMAMLANDI ===")
        print(f"Toplam süre: {sure:.2f} saniye")
        print(f"Toplam ders sayısı: {len(muafiyet_sistemi.ders_kod)}")
        print(f"Muaf olunan ders sayısı: {len(muaf_olunan_dersler)}")
        print(f"Başarı oranı: {len(muaf_olunan_dersler)/len(muafiyet_sistemi.ders_kod)*100:.1f}%")
        
        return muaf_olunan_dersler
        
    except Exception as e:
        print(f"❌ Muafiyet işlemi hatası: {str(e)}")
        raise

def mufredat_derslerini_dosyaya_yaz(mufredat_dosyasi):
    """
    Müfredat dosyasından dersleri çıkarıp mufredat.txt dosyasına yazar
    
    Args:
        mufredat_dosyasi: Müfredat PDF dosyasının yolu
    """
    try:
        # PDF içeriğini oku
        pdf_content = get_cached_pdf_content(mufredat_dosyasi)
        
        # Muafiyet sistemi oluştur
        muafiyet_sistemi = MuafiyetSistemi()
        
        # Müfredatı oku
        muafiyet_sistemi.mufredat_oku(mufredat_dosyasi)
        
        # Dersleri mufredat.txt dosyasına yaz
        with open("mufredat.txt", "w", encoding='utf-8') as f:
            f.write("MÜFREDAT DERSLERİ\n")
            f.write("=" * 50 + "\n\n")
            
            for i in range(len(muafiyet_sistemi.ders_kod_kaynak)):
                ders_kodu = muafiyet_sistemi.ders_kod_kaynak[i]
                ders_adi = muafiyet_sistemi.ders_ad_kaynak[i]
                ders_akts = muafiyet_sistemi.ders_akts_kaynak[i]
                
                f.write(f"Ders Kodu: {ders_kodu}\n")
                f.write(f"Ders Adı: {ders_adi}\n")
                f.write(f"AKTS: {ders_akts}\n")
                f.write("-" * 30 + "\n\n")
        
        print(f"✓ {len(muafiyet_sistemi.ders_kod_kaynak)} ders mufredat.txt dosyasına yazıldı")
        return True
        
    except Exception as e:
        print(f"❌ Müfredat dosyası yazma hatası: {str(e)}")
        return False