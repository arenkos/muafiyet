from PyPDF2 import PdfReader
import re
import spacy
import os

# Transkriptteki geçilen dersleri sıralıyor ve out.txt dosyasına yazıyor
def process_pdf_content(pdf_content, derece):
    lines = pdf_content.split('\n')
    output_lines = []

    for i in range(len(lines) - 2):
        line1 = lines[i]
        line2 = lines[i+1]
        line3 = lines[i+2]

        if line1[0] == '*':
            line1 = line1[1:]
        elif line1[0] == '*' and line1[0] == '*':
            line1 = line1[2:]
        match = re.match(r'(\w+\s\d+)\s(.+)', line1)
        match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line2)

        if match and match2:

            course_code = match.group(1)
            course_name = match.group(2)
            course_name = course_name.replace('\t', ' ')
            akts = match2.group(6)
            grade = int(match2.group(7)) / int(akts)
            if int(match2.group(7)) != 0 or line2.endswith("G"):
                output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

        if line1[0] == '*':
            line1 = line1[1:]
        elif line1[0] == '*' and line1[0] == '*':
            line1 = line1[2:]
        match = re.match(r'(\w+\s\d+)\s(.+)', line1)
        match_ = re.match(r'(.+)', line2)
        match2 = re.match(r'\((.+?)\)\w\s(\w+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(\d+)\s(.+)\s\s(\w+)', line3)

        if match and match_ and match2:
            course_code = match.group(1)
            course_name = match.group(2) + ' ' + match_.group(1)
            course_name = course_name.replace('\t', ' ')
            akts = match2.group(6)
            grade = int(match2.group(7)) / int(akts)
            if int(match2.group(7)) != 0 or line2.endswith("G"):
                output_lines.append(f"{course_code}\t{course_name}\t{akts}\t{grade}\t{derece}")

    with open("output.txt", "w") as f:
        for line in output_lines:
            f.write(line + "\n")
    # print("Tablo başarıyla oluşturuldu ve 'output.txt' dosyasına yazıldı.")

    # Dosyadan metni okuyarak işlem yapacak fonksiyon
    def read_text_from_file(filename):
        with open(filename, 'r') as file:
            text = file.readlines()
        return text

    # Dosyadaki satırları ders koduna göre sıralayacak fonksiyon
    def sort_lines_by_course_code(lines):
        # Satırları ders koduna göre sırala
        sorted_lines = sorted(lines, key=lambda x: x.split(None, 2)[:2])
        return sorted_lines

    # Aynı ders koduna sahip satırları silen fonksiyon
    def remove_duplicate_course_codes(lines):
        unique_lines = []
        seen_codes = set()

        for line in lines:
            parts = line.split()
            if len(parts) < 2:  # Boş veya eksik satırlardan kaçınmak için
                continue

            code = " ".join(parts[:2])  # İlk iki kelimeyi ders kodu olarak al

            if code not in seen_codes:
                unique_lines.append(line)
                seen_codes.add(code)

        return unique_lines

    # Dosya adı
    filename = 'output.txt'

    # Dosyadan metni oku
    lines = read_text_from_file(filename)

    # Satırları ders koduna göre sırala
    sorted_lines = sort_lines_by_course_code(lines)

    # Aynı ders koduna sahip satırları sil
    unique_lines = remove_duplicate_course_codes(sorted_lines)

    if os.path.exists("out.txt"):
        with open("output.txt", 'a') as file:
            file.writelines(unique_lines)
        # Dosyadan metni oku
        lines = read_text_from_file("output.txt")

        # Satırları ders koduna göre sırala
        sorted_lines = sort_lines_by_course_code(lines)

        # Aynı ders koduna sahip satırları sil
        unique_lines = remove_duplicate_course_codes(sorted_lines)

        # Temizlenmiş metni aynı dosyaya yaz
        with open("out.txt", 'w') as file:
            file.writelines(unique_lines)
    else:
        # Temizlenmiş metni aynı dosyaya yaz
        with open("out.txt", 'w') as file:
            file.writelines(unique_lines)

    if os.path.exists("output.txt"):
        os.remove("output.txt")

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
    # PDF dosyasını aç text2 için
    pdf_file = ders_kod_al + '.pdf'

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

    ders_icerik = process_ders_icerik_dogus(text)

    return ders_icerik

# Muafiyet hesaplanmasını yönetmeliğe göre yaparak muaf_olunan_dersler.txt dosyasına yazar
def muafiyet_hesapla():
    kod_say = 0
    ad_say = 0
    akts_say = 0

    muaf_olunan_dersler = []
    for a in range(len(ders_kod_kaynak)):
        for b in range(len(ders_kod)):
            try:
                if ders_kod_kaynak[a] == ders_kod[b] and ders_akts_kaynak[a] >= ders_akts[b]:
                    kod_say = kod_say + 1
                    muaf_olunan_dersler.append(ders_kod_kaynak[a] + " " + ders_ad_kaynak[a] + "\t" + ders_akts_kaynak[a] + "\t" + ders_zs_kaynak[a] + "\t-->\t"
                                               + ders_kod[b] + " " + ders_ad[b] + "\t" + ders_akts[b] + "\t" + ders_not[b])
                    break
                elif check_similarity(ders_ad_kaynak[a], ders_ad[b]) == 1 and check_similarity(ders_icerik_al(ders_kod_kaynak[a]),ders_icerik_al(ders_kod[b])) and ders_akts_kaynak[a] >= ders_akts[b]:
                    ad_say = ad_say + 1
                    muaf_olunan_dersler.append(ders_kod_kaynak[a] + " " + ders_ad_kaynak[a] + "\t" + ders_akts_kaynak[a] + "\t" + ders_zs_kaynak[a] + "\t-->\t"
                                               + ders_kod[b] + " " + ders_ad[b] + "\t" + ders_akts[b] + "\t" + ders_not[b])
                    break
                elif ders_akts_kaynak[a] >= ders_akts[b] and check_similarity(ders_icerik_al(ders_kod_kaynak[a]),ders_icerik_al(ders_kod[b])) == 1:
                    akts_say = akts_say + 1
                    muaf_olunan_dersler.append(ders_kod_kaynak[a] + " " + ders_ad_kaynak[a] + "\t" + ders_akts_kaynak[a] + "\t" + ders_zs_kaynak[a] + "\t-->\t"
                                               + ders_kod[b] + " " + ders_ad[b] + "\t" + ders_akts[b] + "\t" + ders_not[b])
                    break
                else:
                    continue
                pass
            except:
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

# with open("ders_icerik.txt","r") as ders:
    # text1 = ders.read()

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
nlp = spacy.load("en_core_web_sm")

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
        print(ders_kod_kaynak+"\t"+ders_ad_kaynak+"\t"+ders_akts_kaynak+"\t"+ders_zs_kaynak)

#muafiyet_hesapla()