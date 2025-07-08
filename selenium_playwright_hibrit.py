from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from playwright.sync_api import sync_playwright
import os
import re
import time

def normalize_filename(name):
    # Harf ve sayı arasına boşluk koy, diğer özel karakterleri temizle
    name = re.sub(r'([A-ZĞÜŞİÖÇ])_(\d)', r'\1 \2', name.replace('_', ' '))
    name = re.sub(r'([A-ZĞÜŞİÖÇ])(\d)', r'\1 \2', name)
    name = re.sub(r'[^a-zA-Z0-9ğüşiöçĞÜŞİÖÇ ]', '', name)
    return name.strip()

def playwright_html_to_pdf(html, dosya_adi):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        time.sleep(1)
        page.pdf(path=dosya_adi, format="A4")
        browser.close()

def iframe_e_gec(driver):
    """Iframe'e güvenli geçiş yap"""
    try:
        # Ana sayfaya geri dön
        driver.switch_to.default_content()
        time.sleep(1)
        
        # Iframe'i bekle ve bul
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IFRAME1"))
        )
        driver.switch_to.frame(iframe)
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Iframe'e geçiş hatası: {str(e)}")
        return False

def guvenli_tikla(driver, element, ders_kodu):
    """Elemente güvenli tıklama yap"""
    try:
        # Elementi görünür yap
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)
        
        # Önce normal tıklama dene
        try:
            element.click()
            return True
        except:
            pass
        
        # JavaScript ile tıklama dene
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except:
            pass
        
        # Son çare: Actions ile tıklama
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.move_to_element(element).click().perform()
            return True
        except:
            pass
        
        print(f"Tıklama başarısız: {ders_kodu}")
        return False
        
    except Exception as e:
        print(f"Güvenli tıklama hatası: {ders_kodu} - {str(e)}")
        return False

def dersleri_islemle(driver, pdf_klasoru, ders_tipi=""):
    ders_linkleri = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btnDersKod_']")
    print(f"Selenium: {ders_tipi} - Toplam {len(ders_linkleri)} ders bulundu.")
    
    for i in range(len(ders_linkleri)):
        try:
            # Her ders için linkleri yeniden bul
            ders_linkleri_guncel = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btnDersKod_']")
            if i >= len(ders_linkleri_guncel):
                print(f"Selenium: {i+1}. ders linki bulunamadı, atlanıyor...")
                continue
            link = ders_linkleri_guncel[i]
            ders_kodu = link.text.strip()
            print(f"Selenium: {ders_tipi} - Ders {i+1}/{len(ders_linkleri)}: {ders_kodu}")

            # Güvenli tıklama yap
            if not guvenli_tikla(driver, link, ders_kodu):
                print(f"Selenium: {ders_kodu} tıklanamadı, atlanıyor...")
                continue
                
            time.sleep(3)

            # İçerik sayfasının HTML'ini al
            html = driver.page_source
            dosya_adi = os.path.join(pdf_klasoru, f"{normalize_filename(ders_kodu)}.pdf")
            print(f"Playwright: {ders_kodu} PDF indiriliyor...")
            playwright_html_to_pdf(html, dosya_adi)
            print(f"Playwright: PDF kaydedildi: {dosya_adi}")

            # Geri dön
            driver.back()
            time.sleep(2)
            
            # Iframe'e güvenli geçiş
            if not iframe_e_gec(driver):
                print("Iframe'e geçiş başarısız, script durduruluyor...")
                break
                    
        except Exception as e:
            print(f"Hata: {ders_kodu} işlenirken hata oluştu: {str(e)}")
            try:
                # Hata durumunda sayfayı yenile ve iframe'e geç
                driver.refresh()
                time.sleep(3)
                if not iframe_e_gec(driver):
                    print("Hata sonrası iframe'e geçiş başarısız, script durduruluyor...")
                    break
            except:
                print("Hata sonrası kurtarma başarısız, script durduruluyor...")
                break
            continue

def gruplu_dersleri_islemle(driver, pdf_klasoru):
    gruplu_linkler = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btn_EC_Goster_']")
    print(f"Selenium: Gruplu Dersler - Toplam {len(gruplu_linkler)} grup bulundu.")
    
    for i in range(len(gruplu_linkler)):
        try:
            gruplu_linkler_guncel = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btn_EC_Goster_']")
            if i >= len(gruplu_linkler_guncel):
                print(f"Selenium: {i+1}. grup linki bulunamadı, atlanıyor...")
                continue
            grup_link = gruplu_linkler_guncel[i]
            grup_adi = grup_link.text.strip() or f"Grup_{i+1}"
            print(f"Selenium: Gruplu Dersler - Grup {i+1}/{len(gruplu_linkler)}: {grup_adi}")
            
            if not guvenli_tikla(driver, grup_link, grup_adi):
                print(f"Selenium: {grup_adi} tıklanamadı, atlanıyor...")
                continue
                
            time.sleep(2)
            
            # Açılan gruptaki dersleri işle
            dersleri_islemle(driver, pdf_klasoru, ders_tipi=f"Gruplu Dersler - {grup_adi}")
            
            # Geri dön
            driver.back()
            time.sleep(2)
            if not iframe_e_gec(driver):
                print("Grup işlemi sonrası iframe'e geçiş başarısız, script durduruluyor...")
                break
            
        except Exception as e:
            print(f"Hata: {grup_adi} işlenirken hata oluştu: {str(e)}")
            try:
                driver.refresh()
                time.sleep(3)
                if not iframe_e_gec(driver):
                    print("Grup hatası sonrası iframe'e geçiş başarısız, script durduruluyor...")
                    break
            except:
                print("Grup hatası sonrası kurtarma başarısız, script durduruluyor...")
                break
            continue

def hibrit_pdf_indir(url, pdf_klasoru):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    
    print("Selenium: Sol menüde 'Dersler' linki aranıyor...")
    dersler_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dersler')]"))
    )
    dersler_link.click()
    print("Selenium: 'Dersler' linkine tıklandı.")
    time.sleep(3)
    
    print("Selenium: Iframe aranıyor...")
    iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "IFRAME1"))
    )
    driver.switch_to.frame(iframe)
    print("Selenium: Iframe'e geçildi.")
    
    os.makedirs(pdf_klasoru, exist_ok=True)
    
    print("\n=== Normal Dersler İşleniyor ===")
    dersleri_islemle(driver, pdf_klasoru, "Normal Dersler")
    
    print("\n=== Gruplu Dersleri Göster Butonu Aranıyor ===")
    try:
        gruplu_buton = driver.find_element(By.XPATH, "//input[contains(@value, 'Gruplu Dersleri Göster')]")
        gruplu_buton.click()
        print("Selenium: 'Gruplu Dersleri Göster' butonuna tıklandı.")
        time.sleep(3)
    except Exception as e:
        print(f"Gruplu Dersleri Göster butonu bulunamadı veya tıklanamadı: {str(e)}")
    
    print("\n=== Gruplu Dersler İşleniyor ===")
    gruplu_dersleri_islemle(driver, pdf_klasoru)
    
    driver.quit()
    print("\n=== İşlem tamamlandı ===")

if __name__ == "__main__":
    url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
    pdf_klasoru = "icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
    hibrit_pdf_indir(url, pdf_klasoru) 