from PyPDF2 import PdfReader
import re
import spacy
import os

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

# Benzerlik Hesaplama
def semantic_similarity(text1, text2):
    # Metinleri analiz etmek için spaCy kullanın
    doc1 = nlp(text1)
    doc2 = nlp(text2)

    # Belge vektörlerini kullanarak benzerlik hesaplayın
    similarity_score = doc1.similarity(doc2)

    return similarity_score

def check_similarity(text1, text2, threshold=0.7):
    # Anlamsal benzerliği hesaplayın
    similarity_score = semantic_similarity(text1, text2)
    similarity_score = round(similarity_score, 1)

    # Eğer benzerlik skoru belirtilen eşik değerinden büyükse, geçerli çıktı verin
    if similarity_score >= threshold:
        # print("Metinler benzer, benzerlik skoru:", similarity_score)
        return 1
    else:
        # print("Metinler benzer değil, benzerlik skoru:", similarity_score)
        return 0

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

    with open("muaf_olunan_dersler.txt", "w") as f:
        for line in muaf_olunan_dersler:
            f.write(line + "\n")


# PDF dosyasını aç
pdf_file = 'doğuş.pdf'

# PDF okuyucu objesi oluştur
pdf_reader = PdfReader(pdf_file)

# PDF'deki sayfa sayısını al
num_pages = len(pdf_reader.pages)
text = ""

# Her sayfayı oku ve metni çıkart
for page in range(num_pages):
    # Sayfayı al
    pdf_page = pdf_reader.pages[page]

    # Sayfanın metnini çıkart
    text = text + pdf_page.extract_text()

# PDF dosyasının içeriği
pdf_content = text

derece = ""
aranan_kelime = "Akademik Derece Türü:Önlisans"
if aranan_kelime in text:
    derece = "Önlisans"
else:
    derece = "Lisans"

process_pdf_content(pdf_content, derece)


# PDF dosyasını aç text1 için
pdf_file = 'd_f.pdf'

# PDF okuyucu objesi oluştur
pdf_reader = PdfReader(pdf_file)

# PDF'deki sayfa sayısını al
num_pages = len(pdf_reader.pages)
text = ""

# Her sayfayı oku ve metni çıkart
for page in range(num_pages):
    # Sayfayı al
    pdf_page = pdf_reader.pages[page]

    # Sayfanın metnini çıkart
    text = text + pdf_page.extract_text()

# PDF dosyasının içeriği text1
text1 = text

with open("ders_icerik.txt","r") as ders:
    text1 = ders.read()

# PDF dosyasını aç text2 için
pdf_file = 'm_f.pdf'

# PDF okuyucu objesi oluştur
pdf_reader = PdfReader(pdf_file)

# PDF'deki sayfa sayısını al
num_pages = len(pdf_reader.pages)
text = ""

# Her sayfayı oku ve metni çıkart
for page in range(num_pages):
    # Sayfayı al
    pdf_page = pdf_reader.pages[page]

    # Sayfanın metnini çıkart
    text = text + pdf_page.extract_text()

# PDF dosyasının içeriği text2
text2 = text

# spaCy'yi kullanarak dil modelini yükleyin
nlp = spacy.load("en_core_web_md")

# PDF dosyasını aç text2 için
pdf_file = 'd_m2.pdf'

# PDF okuyucu objesi oluştur
pdf_reader = PdfReader(pdf_file)

# PDF'deki sayfa sayısını al
num_pages = len(pdf_reader.pages)
text = ""

# Her sayfayı oku ve metni çıkart
for page in range(num_pages):
    # Sayfayı al
    pdf_page = pdf_reader.pages[page]

    # Sayfanın metnini çıkart
    text = text + pdf_page.extract_text()

# PDF dosyasının içeriği
text3 = text

icerik1 = []
icerik1 = process_ders_icerik_dogus(text3)
dize = ''
for öğe in icerik1:
    dize += öğe + '\n'

# Benzerlik kontrolü yapın
# check_similarity(dize, text2)

ders_kodlari = []
with open("out.txt","r") as dersler:
    ders_kodlari = dersler.readlines()

ders_say = 0
ders_kod = []
ders_ad = []
ders_akts = []
ders_not = []

for ders_say in range(len(ders_kodlari)):
    d = re.match(r'(.*)\t(.*)\t(\d+)\t(.*)\n', ders_kodlari[ders_say])
    if d:
        ders_kod.append(d.group(1))
        ders_ad.append(d.group(2))
        ders_akts.append(d.group(3))
        ders_not.append(d.group(4))

# PDF dosyasını aç
pdf_file = 'mufredat_dogus.pdf'

# PDF okuyucu objesi oluştur
pdf_reader = PdfReader(pdf_file)

# PDF'deki sayfa sayısını al
num_pages = len(pdf_reader.pages)
text = ""

# Her sayfayı oku ve metni çıkart
for page in range(num_pages):
    # Sayfayı al
    pdf_page = pdf_reader.pages[page]

    # Sayfanın metnini çıkart
    text = text + pdf_page.extract_text()

# PDF dosyasının içeriği
text = text.split("\n")

ders_kod_kaynak = []
ders_ad_kaynak = []
ders_akts_kaynak = []
ders_zs_kaynak = []
for a in range(len(text)):
    zorunlu = re.match(r'(\w+\s\d+)\s(.*)\s(\d+)\s(.*)', text[a])
    m = re.match(r'(\w+\s\d+)\s(.*)\s(\d+)\s(.*)\s(\w+)', text[a])
    if m:
        ders_kod_kaynak.append(m.group(1))
        ders_ad_kaynak.append(m.group(4))
        ders_akts_kaynak.append(m.group(3))
        ders_zs_kaynak.append(m.group(5))

#muafiyet_hesapla()

class MuafiyetSistemi:
    def __init__(self):
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
        """Metinler arası benzerliği hesaplar"""
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        return doc1.similarity(doc2)

    def ders_icerik_al(self, ders_kodu):
        """Ders içeriğini okur"""
        try:
            # Boşlukları kaldır ve sayı ile harf arasına boşluk ekle
            ders_kodu = re.sub(r'\s+', '', ders_kodu)  # Tüm boşlukları kaldır
            ders_kodu = re.sub(r'(\w)(\d+)', r'\1 \2', ders_kodu)  # Sayı ve harf arasına boşluk ekle
            if '\t' in ders_kodu:
                ders_kodu.lstrip('\t')
            pdf_file = f'{ders_kodu}.pdf'
            self._check_file_exists(pdf_file)
            
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
                
            return self.process_ders_icerik_dogus(text)
            
        except Exception as e:
            print(f"Ders içeriği okuma hatası: {str(e)}")
            return []

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

    def transkript_oku(self, pdf_path):
        """Transkript PDF'ini okur ve işler"""
        try:
            self._check_file_exists(pdf_path)
            pdf_reader = PdfReader(pdf_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
                
            derece = "Önlisans" if "Akademik Derece Türü:Önlisans" in text else "Lisans"
            self.process_pdf_content(text, derece)
            
            # Dosyadan dersleri oku
            with open("out.txt", "r", encoding='utf-8') as f:
                ders_kodlari = f.readlines()
                
            for line in ders_kodlari:
                match = re.match(r'(.*)\t(.*)\t(\d+)\t(.*)\n', line)
                if match:
                    self.ders_kod.append(match.group(1))
                    self.ders_ad.append(match.group(2))
                    self.ders_akts.append(match.group(3))
                    self.ders_not.append(match.group(4))
                    
        except Exception as e:
            print(f"Transkript okuma hatası: {str(e)}")

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
                        
                        # Ders içeriği benzerliği kontrolü
                        kaynak_icerik = self.ders_icerik_al(self.ders_kod_kaynak[i])
                        hedef_icerik = self.ders_icerik_al(self.ders_kod[j])
                        if not kaynak_icerik == [] and not hedef_icerik == []:
                            if self.check_similarity(" ".join(kaynak_icerik), " ".join(hedef_icerik)) >= similarity_threshold:
                                self._add_muaf_ders(muaf_olunan_dersler, i, j)
                                break
                            
                except Exception as e:
                    print(f"Muafiyet hesaplama hatası: {str(e)}")
                    continue

        # Sonuçları dosyaya yaz
        with open("muaf_olunan_dersler.txt", "w", encoding='utf-8') as f:
            for line in muaf_olunan_dersler:
                f.write(line + "\n")

def main():
    try:
        # Muafiyet sistemi başlat
        sistem = MuafiyetSistemi()
        
        # Dosyaları oku
        sistem.transkript_oku("doğuş.pdf")
        sistem.mufredat_oku("mufredat_dogus.pdf")
        
        # Muafiyet hesapla
        sistem.muafiyet_hesapla()
        
        print("İşlem başarıyla tamamlandı. Sonuçlar 'muaf_olunan_dersler.txt' dosyasına kaydedildi.")
        
    except Exception as e:
        print(f"Program hatası: {str(e)}")

if __name__ == "__main__":
    main()