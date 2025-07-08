#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Doğuş Üniversitesi OBS Ders İçerikleri PDF İndirme Scripti
Ubuntu Sunucu Uyumlu - Headless Mod
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from playwright.sync_api import sync_playwright
import os
import re
import time
import logging
from datetime import datetime

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('muafiyet_indir.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def normalize_filename(name):
    """Dosya adını normalize et - harf ve sayı arasına boşluk koy"""
    name = re.sub(r'([A-ZĞÜŞİÖÇ])_(\d)', r'\1 \2', name.replace('_', ' '))
    name = re.sub(r'([A-ZĞÜŞİÖÇ])(\d)', r'\1 \2', name)
    name = re.sub(r'[^a-zA-Z0-9ğüşiöçĞÜŞİÖÇ ]', '', name)
    return name.strip()

def playwright_html_to_pdf(html, dosya_adi):
    """HTML içeriğini PDF'e çevir"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            time.sleep(2)
            page.pdf(path=dosya_adi, format="A4")
            browser.close()
            logger.info(f"PDF başarıyla kaydedildi: {dosya_adi}")
    except Exception as e:
        logger.error(f"PDF kaydetme hatası: {str(e)}")
        raise

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
        logger.error(f"Iframe'e geçiş hatası: {str(e)}")
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
        
        logger.warning(f"Tıklama başarısız: {ders_kodu}")
        return False
        
    except Exception as e:
        logger.error(f"Güvenli tıklama hatası: {ders_kodu} - {str(e)}")
        return False

def dersleri_islemle(driver, pdf_klasoru, ders_tipi=""):
    """Belirli bir ders listesini işle"""
    try:
        ders_linkleri = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btnDersKod_']")
        logger.info(f"{ders_tipi} - Toplam {len(ders_linkleri)} ders bulundu.")
        
        for i in range(len(ders_linkleri)):
            try:
                # Her ders için linkleri yeniden bul
                ders_linkleri_guncel = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btnDersKod_']")
                if i >= len(ders_linkleri_guncel):
                    logger.warning(f"{i+1}. ders linki bulunamadı, atlanıyor...")
                    continue
                
                link = ders_linkleri_guncel[i]
                ders_kodu = link.text.strip()
                logger.info(f"{ders_tipi} - Ders {i+1}/{len(ders_linkleri)}: {ders_kodu}")

                # Güvenli tıklama yap
                if not guvenli_tikla(driver, link, ders_kodu):
                    logger.warning(f"{ders_kodu} tıklanamadı, atlanıyor...")
                    continue
                    
                time.sleep(3)

                # İçerik sayfasının HTML'ini al
                html = driver.page_source
                dosya_adi = os.path.join(pdf_klasoru, f"{normalize_filename(ders_kodu)}.pdf")
                
                logger.info(f"PDF indiriliyor: {ders_kodu}")
                playwright_html_to_pdf(html, dosya_adi)

                # Geri dön
                driver.back()
                time.sleep(2)
                
                # Iframe'e güvenli geçiş
                if not iframe_e_gec(driver):
                    logger.error("Iframe'e geçiş başarısız, script durduruluyor...")
                    break
                        
            except Exception as e:
                logger.error(f"Hata: {ders_kodu} işlenirken hata oluştu: {str(e)}")
                try:
                    # Hata durumunda sayfayı yenile ve iframe'e geç
                    driver.refresh()
                    time.sleep(3)
                    if not iframe_e_gec(driver):
                        logger.error("Hata sonrası iframe'e geçiş başarısız, script durduruluyor...")
                        break
                except:
                    logger.error("Hata sonrası kurtarma başarısız, script durduruluyor...")
                    break
                continue
    except Exception as e:
        logger.error(f"Dersler işlenirken genel hata: {str(e)}")

def gruplu_dersleri_islemle(driver, pdf_klasoru):
    """Gruplu dersleri işle"""
    try:
        gruplu_linkler = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btn_EC_Goster_']")
        logger.info(f"Gruplu Dersler - Toplam {len(gruplu_linkler)} grup bulundu.")
        
        for i in range(len(gruplu_linkler)):
            try:
                gruplu_linkler_guncel = driver.find_elements(By.CSS_SELECTOR, "a[id^='grdBolognaDersler_btn_EC_Goster_']")
                if i >= len(gruplu_linkler_guncel):
                    logger.warning(f"{i+1}. grup linki bulunamadı, atlanıyor...")
                    continue
                
                grup_link = gruplu_linkler_guncel[i]
                grup_adi = grup_link.text.strip() or f"Grup_{i+1}"
                logger.info(f"Gruplu Dersler - Grup {i+1}/{len(gruplu_linkler)}: {grup_adi}")
                
                if not guvenli_tikla(driver, grup_link, grup_adi):
                    logger.warning(f"{grup_adi} tıklanamadı, atlanıyor...")
                    continue
                    
                time.sleep(2)
                
                # Açılan gruptaki dersleri işle
                dersleri_islemle(driver, pdf_klasoru, ders_tipi=f"Gruplu Dersler - {grup_adi}")
                
                # Geri dön
                driver.back()
                time.sleep(2)
                if not iframe_e_gec(driver):
                    logger.error("Grup işlemi sonrası iframe'e geçiş başarısız, script durduruluyor...")
                    break
                
            except Exception as e:
                logger.error(f"Hata: {grup_adi} işlenirken hata oluştu: {str(e)}")
                try:
                    driver.refresh()
                    time.sleep(3)
                    if not iframe_e_gec(driver):
                        logger.error("Grup hatası sonrası iframe'e geçiş başarısız, script durduruluyor...")
                        break
                except:
                    logger.error("Grup hatası sonrası kurtarma başarısız, script durduruluyor...")
                    break
                continue
    except Exception as e:
        logger.error(f"Gruplu dersler işlenirken genel hata: {str(e)}")

def hibrit_pdf_indir(url, pdf_klasoru):
    """Ana fonksiyon - Hibrit yaklaşım: Selenium + Playwright"""
    logger.info("=== Ders İçerikleri PDF İndirme Başlıyor ===")
    
    # Chrome options - Ubuntu sunucu için
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Headless mod
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('--disable-javascript')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        # Chrome driver başlat
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome driver başlatıldı")
        
        # Sayfaya git
        logger.info(f"Sayfaya gidiliyor: {url}")
        driver.get(url)
        
        # Sol menüden 'Dersler' linkine tıkla
        logger.info("Sol menüde 'Dersler' linki aranıyor...")
        dersler_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dersler')]"))
        )
        dersler_link.click()
        logger.info("'Dersler' linkine tıklandı.")
        time.sleep(3)
        
        # Iframe'e geç
        logger.info("Iframe aranıyor...")
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "IFRAME1"))
        )
        driver.switch_to.frame(iframe)
        logger.info("Iframe'e geçildi.")
        
        # PDF klasörünü oluştur
        os.makedirs(pdf_klasoru, exist_ok=True)
        
        # Normal dersleri işle
        logger.info("=== Normal Dersler İşleniyor ===")
        dersleri_islemle(driver, pdf_klasoru, "Normal Dersler")
        
        # Gruplu dersleri göster butonunu ara ve tıkla
        logger.info("=== Gruplu Dersleri Göster Butonu Aranıyor ===")
        try:
            gruplu_buton = driver.find_element(By.XPATH, "//input[contains(@value, 'Gruplu Dersleri Göster')]")
            gruplu_buton.click()
            logger.info("'Gruplu Dersleri Göster' butonuna tıklandı.")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"Gruplu Dersleri Göster butonu bulunamadı: {str(e)}")
        
        # Gruplu dersleri işle
        logger.info("=== Gruplu Dersler İşleniyor ===")
        gruplu_dersleri_islemle(driver, pdf_klasoru)
        
        logger.info("=== İşlem Başarıyla Tamamlandı ===")
        
    except Exception as e:
        logger.error(f"Genel hata: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver kapatıldı")

if __name__ == "__main__":
    # Konfigürasyon
    url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
    pdf_klasoru = "icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
    
    # Başlangıç zamanı
    baslangic_zamani = datetime.now()
    logger.info(f"İşlem başlangıç zamanı: {baslangic_zamani}")
    
    try:
        hibrit_pdf_indir(url, pdf_klasoru)
        
        # Bitiş zamanı ve süre hesaplama
        bitis_zamani = datetime.now()
        sure = bitis_zamani - baslangic_zamani
        logger.info(f"İşlem bitiş zamanı: {bitis_zamani}")
        logger.info(f"Toplam süre: {sure}")
        
    except Exception as e:
        logger.error(f"Script çalıştırılırken hata oluştu: {str(e)}")
        raise 