import unicodedata
import os

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

def test_file_matching():
    """Dosya eşleştirme testi"""
    parent_path = "./mufredat/DOĞUŞ ÜNİVERSİTESİ"
    file_name = "Yazılım Mühendisliği.pdf"
    
    print(f"Looking for: {file_name}")
    print(f"In directory: {parent_path}")
    
    normalized_file_name = normalize_string(file_name)
    print(f"Normalized file name: {normalized_file_name}")
    
    print("\nAvailable files:")
    for item in os.listdir(parent_path):
        if os.path.isfile(os.path.join(parent_path, item)):
            normalized_item = normalize_string(item)
            print(f"  - {item} -> {normalized_item}")
            if normalized_item == normalized_file_name:
                print(f"    *** MATCH FOUND! ***")
                return os.path.join(parent_path, item)
    
    print("\nNo match found!")
    return None

if __name__ == "__main__":
    result = test_file_matching()
    if result:
        print(f"\nFound file: {result}")
    else:
        print("\nNo matching file found.") 