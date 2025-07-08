from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
import zipfile
import shutil
from main import MuafiyetSistemi, muafiyet_islem_baslat, mufredat_derslerini_dosyaya_yaz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import unicodedata

app = Flask(__name__)
app.secret_key = 'muafiyet_secret_key'

UPLOAD_FOLDER = 'uploads'
EXTRACT_FOLDER = 'extracted'
SONUCLAR_FOLDER = 'sonuclar'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
os.makedirs(SONUCLAR_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dummy veriler (dinamik seçim için dict yapısı)
UNIVERSITIES = ['Doğuş Üniversitesi', 'Nişantaşı Üniversitesi', 'Medeniyet Üniversitesi']
FAKULTELER = {
    'Doğuş Üniversitesi': ['Mühendislik Fakültesi', 'Fen-Edebiyat Fakültesi'],
    'Nişantaşı Üniversitesi': ['Mühendislik Fakültesi'],
    'Medeniyet Üniversitesi': ['Fen-Edebiyat Fakültesi']
}
BOLUMLER = {
    'Doğuş Üniversitesi': {
        'Mühendislik Fakültesi': ['Yazılım Mühendisliği', 'Elektrik-Elektronik Mühendisliği'],
        'Fen-Edebiyat Fakültesi': ['Matematik', 'Fizik']
    },
    'Nişantaşı Üniversitesi': {
        'Mühendislik Fakültesi': ['Yazılım Mühendisliği']
    },
    'Medeniyet Üniversitesi': {
        'Fen-Edebiyat Fakültesi': ['Kimya', 'Biyoloji']
    }
}
OGRENCILER = ['Ali Yılmaz', 'Ayşe Demir', 'Mehmet Kaya']

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

def extract_zip_file(zip_path, student_id):
    """Zip dosyasını öğrenci numarası ile isimlendirilmiş klasöre çıkarır"""
    extract_path = os.path.join(EXTRACT_FOLDER, student_id)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    os.makedirs(extract_path, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    return extract_path

def get_transkript_files(extract_path, universite, bolum):
    """Transkript klasöründeki tüm PDF dosyalarını analiz eder"""
    print(f"DEBUG: Extract path: {extract_path}")
    
    # Extract edilen klasörün içeriğini kontrol et
    extract_contents = os.listdir(extract_path)
    print(f"DEBUG: Extract folder contents: {extract_contents}")
    
    # Eğer tek bir klasör varsa, onun içinde transkript klasörünü ara
    if len(extract_contents) == 1 and os.path.isdir(os.path.join(extract_path, extract_contents[0])):
        subfolder = extract_contents[0]
        # Case-insensitive transkript klasörü ara
        subfolder_path = os.path.join(extract_path, subfolder)
        transkript_folder = find_case_insensitive_folder(subfolder_path, 'transkript')
        print(f"DEBUG: Found subfolder: {subfolder}")
        print(f"DEBUG: Looking for transkript in: {transkript_folder}")
    else:
        # Doğrudan extract edilen klasörde transkript klasörünü ara
        transkript_folder = find_case_insensitive_folder(extract_path, 'transkript')
        print(f"DEBUG: Looking for transkript directly in: {transkript_folder}")
    
    print(f"DEBUG: Transkript folder exists: {os.path.exists(transkript_folder)}")
    
    if not os.path.exists(transkript_folder):
        # Extract edilen klasörün içeriğini listele
        print(f"DEBUG: Extract folder contents:")
        if os.path.exists(extract_path):
            for item in os.listdir(extract_path):
                item_path = os.path.join(extract_path, item)
                print(f"  - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
                if os.path.isdir(item_path):
                    sub_contents = os.listdir(item_path)
                    print(f"    Subfolder contents: {sub_contents}")
        raise FileNotFoundError(f"Transkript klasörü bulunamadı: {transkript_folder}")
    
    transkript_files = []
    
    # Transkript klasöründeki tüm PDF dosyalarını bul
    for filename in os.listdir(transkript_folder):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(transkript_folder, filename)
            transkript_files.append(file_path)
            print(f"DEBUG: Found transkript file: {file_path}")
    
    if not transkript_files:
        raise FileNotFoundError("Transkript klasöründe PDF dosyası bulunamadı")
    
    print(f"DEBUG: Total transkript files found: {len(transkript_files)}")
    return transkript_files

def find_case_insensitive_folder(parent_path, folder_name):
    """Case-insensitive olarak klasör arar"""
    print(f"DEBUG: find_case_insensitive_folder - parent_path: {parent_path}, folder_name: {folder_name}")
    
    if not os.path.exists(parent_path):
        print(f"DEBUG: Parent path does not exist: {parent_path}")
        return os.path.join(parent_path, folder_name)
    
    print(f"DEBUG: Parent path contents: {os.listdir(parent_path)}")
    
    normalized_folder_name = normalize_string(folder_name)
    print(f"DEBUG: Normalized folder name: {normalized_folder_name}")
    
    for item in os.listdir(parent_path):
        item_path = os.path.join(parent_path, item)
        normalized_item = normalize_string(item)
        print(f"DEBUG: Checking item: {item} (normalized: {normalized_item}) (is_dir: {os.path.isdir(item_path)})")
        if os.path.isdir(item_path) and normalized_item == normalized_folder_name:
            print(f"DEBUG: Found matching folder: {item}")
            return item_path  # Bulunan klasörün tam yolunu döndür
    
    print(f"DEBUG: No matching folder found, returning: {os.path.join(parent_path, folder_name)}")
    # Eğer bulunamazsa, orijinal yolu döndür
    return os.path.join(parent_path, folder_name)

def get_transkript_file(extract_path, universite, bolum):
    """Transkript klasöründen üniversite-bölüm formatında dosyayı bulur (geriye dönük uyumluluk için)"""
    transkript_folder = os.path.join(extract_path, 'transkript')
    if not os.path.exists(transkript_folder):
        raise FileNotFoundError("Transkript klasörü bulunamadı")
    
    # Üniversite-bölüm formatında dosya adı oluştur
    filename = f"{universite}-{bolum}.pdf"
    transkript_file = os.path.join(transkript_folder, filename)
    
    if not os.path.exists(transkript_file):
        raise FileNotFoundError(f"Transkript dosyası bulunamadı: {filename}")
    
    return [transkript_file]  # Liste olarak döndür

def get_mufredat_file(universite, bolum):
    """Müfredat klasöründen üniversite ve bölüm ismiyle kaydedilen dosyayı alır"""
    # Case-insensitive klasör ve dosya arama
    mufredat_base = find_case_insensitive_folder('.', 'mufredat')
    print(f"DEBUG: Mufredat base: {mufredat_base}")
    
    universite_folder = find_case_insensitive_folder(mufredat_base, universite)
    print(f"DEBUG: Looking for universite: {universite}")
    print(f"DEBUG: Found universite folder: {universite_folder}")
    print(f"DEBUG: Universite folder exists: {os.path.exists(universite_folder)}")
    
    mufredat_file = find_case_insensitive_file(universite_folder, f"{bolum}.pdf")
    print(f"DEBUG: Looking for bolum: {bolum}")
    print(f"DEBUG: Found mufredat file: {mufredat_file}")
    print(f"DEBUG: Mufredat file exists: {os.path.exists(mufredat_file)}")
    
    if not os.path.exists(mufredat_file):
        # Klasör içeriğini listele
        print(f"DEBUG: Universite folder contents:")
        if os.path.exists(universite_folder):
            for item in os.listdir(universite_folder):
                item_path = os.path.join(universite_folder, item)
                print(f"  - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
        raise FileNotFoundError(f"Müfredat dosyası bulunamadı: {mufredat_file}")
    return mufredat_file

def get_ders_icerik_file(universite, bolum, ders_kodu):
    """İçerikler klasöründen üniversite ve bölüm adıyla isimlendirilmiş klasörün içindeki ders koduyla isimlendirilmiş dosyayı alır"""
    # Case-insensitive klasör ve dosya arama
    icerikler_base = find_case_insensitive_folder('.', 'icerikler')
    print(f"DEBUG: Icerikler base: {icerikler_base}")
    
    universite_folder = find_case_insensitive_folder(icerikler_base, universite)
    print(f"DEBUG: Looking for universite in icerikler: {universite}")
    print(f"DEBUG: Found universite folder in icerikler: {universite_folder}")
    
    bolum_folder = find_case_insensitive_folder(universite_folder, bolum)
    print(f"DEBUG: Looking for bolum in icerikler: {bolum}")
    print(f"DEBUG: Found bolum folder in icerikler: {bolum_folder}")
    
    icerik_file = find_case_insensitive_file(bolum_folder, f"{ders_kodu}.pdf")
    print(f"DEBUG: Looking for ders icerik: {ders_kodu}.pdf")
    print(f"DEBUG: Found icerik file: {icerik_file}")
    
    if not os.path.exists(icerik_file):
        raise FileNotFoundError(f"Ders içerik dosyası bulunamadı: {icerik_file}")
    return icerik_file

def find_case_insensitive_file(parent_path, file_name):
    """Case-insensitive olarak dosya arar"""
    print(f"DEBUG: find_case_insensitive_file - parent_path: {parent_path}, file_name: {file_name}")
    
    if not os.path.exists(parent_path):
        print(f"DEBUG: Parent path does not exist: {parent_path}")
        return os.path.join(parent_path, file_name)
    
    print(f"DEBUG: Parent path contents: {os.listdir(parent_path)}")
    
    normalized_file_name = normalize_string(file_name)
    print(f"DEBUG: Normalized file name: {normalized_file_name}")
    
    for item in os.listdir(parent_path):
        item_path = os.path.join(parent_path, item)
        normalized_item = normalize_string(item)
        print(f"DEBUG: Checking item: {item} (normalized: {normalized_item}) (is_file: {os.path.isfile(item_path)})")
        if os.path.isfile(item_path) and normalized_item == normalized_file_name:
            print(f"DEBUG: Found matching file: {item}")
            return item_path
    
    print(f"DEBUG: No matching file found for '{file_name}' (normalized: '{normalized_file_name}')")
    print(f"DEBUG: Available files (normalized):")
    for item in os.listdir(parent_path):
        item_path = os.path.join(parent_path, item)
        if os.path.isfile(item_path):
            normalized_item = normalize_string(item)
            print(f"  - '{item}' -> '{normalized_item}'")
    
    print(f"DEBUG: Returning: {os.path.join(parent_path, file_name)}")
    # Eğer bulunamazsa, orijinal yolu döndür
    return os.path.join(parent_path, file_name)

def create_result_pdf(ogrenci_ad, ogrenci_soyad, ogrenci_no, result_text):
    """Sonuçları PDF olarak kaydeder"""
    filename = f"{ogrenci_ad} {ogrenci_soyad} - {ogrenci_no}.pdf"
    filepath = os.path.join(SONUCLAR_FOLDER, filename)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Başlık
    c.drawString(100, 750, "MUAFİYET RAPORU")
    c.drawString(100, 730, f"Öğrenci: {ogrenci_ad} {ogrenci_soyad}")
    c.drawString(100, 710, f"Öğrenci No: {ogrenci_no}")
    c.drawString(100, 690, "-" * 50)
    
    # Sonuçları yaz
    y_position = 650
    lines = result_text.split('\n')
    for line in lines:
        if y_position < 50:  # Sayfa sonu kontrolü
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = 750
        c.drawString(100, y_position, line)
        y_position -= 15
    
    c.save()
    return filepath

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        universite = request.form.get('universite')
        fakulte = request.form.get('fakulte')
        bolum = request.form.get('bolum')
        ogrenci_ad = request.form.get('ogrenci_ad')
        ogrenci_soyad = request.form.get('ogrenci_soyad')
        ogrenci_no = request.form.get('ogrenci_no')
        zip_file = request.files.get('zip_file')
        similarity_method = request.form.get('similarity_method')
        
        if not (universite and fakulte and bolum and ogrenci_ad and ogrenci_soyad and ogrenci_no and zip_file and similarity_method):
            flash('Lütfen tüm alanları doldurun ve dosyaları yükleyin!', 'danger')
            return redirect(url_for('index'))
        
        try:
            # Zip dosyasını kaydet
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(zip_file.filename))
            zip_file.save(zip_path)
            
            # Öğrenci ID'sini oluştur
            student_id = f"{ogrenci_ad}_{ogrenci_soyad}_{ogrenci_no}".replace(' ', '_').lower()
            
            # Zip dosyasını extract et
            extract_path = extract_zip_file(zip_path, student_id)
            
            # Transkript dosyalarını al
            transkript_paths = get_transkript_files(extract_path, universite, bolum)
            
            # Müfredat dosyasını al (üniversite ve bölüm)
            mufredat_path = get_mufredat_file(universite, bolum)
            
            # Müfredat derslerini mufredat.txt dosyasına yaz
            print("Müfredat dersleri mufredat.txt dosyasına yazılıyor...")
            mufredat_yazildi = mufredat_derslerini_dosyaya_yaz(mufredat_path)
            if mufredat_yazildi:
                print("✓ Müfredat dersleri mufredat.txt dosyasına yazıldı")
            else:
                print("⚠️ Müfredat dersleri dosyaya yazılamadı")
            
            # Muafiyet işlemlerini başlat
            use_gemini = (similarity_method == 'gemini')
            
            # Yeni muafiyet işlem fonksiyonunu kullan
            muaf_olunan_dersler = muafiyet_islem_baslat(zip_path, universite, bolum, use_gemini)
            
            # Sonuç dosyasını oku
            try:
                with open('muaf_olunan_dersler.txt', 'r', encoding='utf-8') as f:
                    result = f.read()
                
                # PDF olarak kaydet
                pdf_path = create_result_pdf(ogrenci_ad, ogrenci_soyad, ogrenci_no, result)
                flash(f'Muafiyet işlemleri tamamlandı. Sonuç dosyası: {pdf_path}', 'success')
                
            except Exception as e:
                result = f'Hata: {str(e)}'
                flash(f'Hata: {str(e)}', 'danger')
            
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('index'))
        
        return render_template('index.html', universities=UNIVERSITIES, fakulteler=FAKULTELER, bolumler=BOLUMLER, result=result)
    
    return render_template('index.html', universities=UNIVERSITIES, fakulteler=FAKULTELER, bolumler=BOLUMLER, result=None)

@app.route('/get_fakulteler', methods=['POST'])
def get_fakulteler():
    universite = request.json.get('universite')
    fakulteler = FAKULTELER.get(universite, [])
    return jsonify({'fakulteler': fakulteler})

@app.route('/get_bolumler', methods=['POST'])
def get_bolumler():
    universite = request.json.get('universite')
    fakulte = request.json.get('fakulte')
    bolumler = BOLUMLER.get(universite, {}).get(fakulte, [])
    return jsonify({'bolumler': bolumler})

if __name__ == '__main__':
    app.run(debug=True) 