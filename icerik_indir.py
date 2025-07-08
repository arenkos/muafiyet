from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import re

class IcerikIndirici:
    def __init__(self):
        """Selenium web driver'ı başlatır"""
        self.chrome_options = Options()
        # Tarayıcıyı arka planda çalıştır (opsiyonel)
        # self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        
        # PDF indirme ayarları
        download_dir = os.getcwd() + "/icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
        self.chrome_options.add_experimental_option(
            "prefs", {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "print.always_print_as_pdf": True,
                "print.default_destination_selection_rules": {
                    "kind": "local",
                    "namePattern": "Save as PDF"
                },
                "download.open_pdf_in_system_reader": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
        )
        
        self.driver = None
        self.wait = None
        
    def tarayici_baslat(self):
        """Chrome tarayıcısını başlatır"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            print("Tarayıcı başarıyla başlatıldı")
            return True
        except Exception as e:
            print(f"Tarayıcı başlatma hatası: {str(e)}")
            return False
    
    def obs_sayfasina_git(self):
        """OBS sayfasına gider"""
        try:
            url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
            self.driver.get(url)
            print("OBS sayfasına gidildi")
            
            # Sayfanın yüklenmesini bekle
            time.sleep(3)
            return True
        except Exception as e:
            print(f"OBS sayfasına gitme hatası: {str(e)}")
            return False
    
    def dersler_linkine_tikla(self):
        """Sol menüden 'Dersler' linkine tıklar ve gerekirse iframe'e geçer"""
        try:
            # Dersler linkini bul ve tıkla
            dersler_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dersler')]"))
            )
            dersler_link.click()
            print("Dersler linkine tıklandı")
            time.sleep(2)
            # Sayfa kaynağını kaydet
            with open("dersler_sayfa_kaynagi.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("Sayfa kaynağı 'dersler_sayfa_kaynagi.html' olarak kaydedildi.")
            # IFRAME kontrolü
            try:
                iframe = self.driver.find_element(By.ID, "IFRAME1")
                self.driver.switch_to.frame(iframe)
                print("IFRAME1 içine geçildi.")
                time.sleep(2)
            except Exception as e:
                print("IFRAME1 bulunamadı veya geçiş yapılamadı:", e)
            return True
        except TimeoutException:
            print("Dersler linki bulunamadı")
            return False
        except Exception as e:
            print(f"Dersler linkine tıklama hatası: {str(e)}")
            return False
    
    def ders_kodlarini_bul(self):
        """Sayfadaki tüm ders kodlarını bulur"""
        try:
            time.sleep(3)  # Sayfanın yüklenmesini bekle
            ders_linkleri = self.driver.find_elements(By.XPATH, "//a[starts-with(@id, 'grdBolognaDersler_btnDersKod_')]")
            ders_kodlari = []
            for link in ders_linkleri:
                kod = link.text.strip()
                link_id = link.get_attribute('id')
                print(f"Link bulundu - ID: {link_id}, Text: '{kod}'")
                if kod and len(kod) > 0:
                    ders_kodlari.append(kod)
            print(f"Toplam bulunan ders kodları: {ders_kodlari}")
            return ders_kodlari
        except Exception as e:
            print(f"Ders kodları bulma hatası: {str(e)}")
            return []
    
    def ders_icerigini_indir(self, ders_kodu):
        """Belirli bir dersin içeriğini indirir"""
        try:
            # Ders koduna tıkla
            ders_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//a[text()='{ders_kodu}']"))
            )
            ders_link.click()
            print(f"{ders_kodu} dersine tıklandı")
            time.sleep(3)
            
            # Sayfanın URL'sini al
            current_url = self.driver.current_url
            print(f"{ders_kodu} sayfası URL: {current_url}")
            
            # PDF olarak sayfayı kaydet
            dosya_adi = f"{ders_kodu.replace(' ', '')}.pdf"
            hedef_klasor = "icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
            
            # Klasörü oluştur
            os.makedirs(hedef_klasor, exist_ok=True)
            
            # PDF olarak sayfayı kaydet
            pdf_path = os.path.join(hedef_klasor, dosya_adi)
            
            print(f"{ders_kodu} için PDF kaydetme başlatıldı")
            
            # Sayfayı PDF olarak kaydet
            try:
                # Önce sayfanın tam yüklenmesini bekle
                time.sleep(2)
                
                # Chrome'un PDF yazdırma özelliğini kullan
                print(f"{ders_kodu} için print() çağrılıyor...")
                
                # Farklı print yöntemlerini dene
                print_methods = [
                    "window.print();",
                    "document.execCommand('print');",
                    "window.print ? window.print() : document.execCommand('print');"
                ]
                
                print_dialog_opened = False
                for method in print_methods:
                    try:
                        self.driver.execute_script(method)
                        print(f"{ders_kodu} için {method} çağrıldı")
                        time.sleep(3)
                        
                        # Print dialog'unun açılıp açılmadığını kontrol et
                        page_source = self.driver.page_source
                        if "Save" in page_source or "Kaydet" in page_source or "print" in page_source.lower():
                            print(f"{ders_kodu} için print dialog'u açıldı")
                            print_dialog_opened = True
                            break
                    except Exception as e:
                        print(f"{ders_kodu} için {method} hatası: {e}")
                        continue
                
                if not print_dialog_opened:
                    print(f"{ders_kodu} için print dialog'u açılamadı")
                
                # PDF dialog'unda Save butonunu bul
                try:
                    # Önce ana sayfada Save butonunu ara
                    print(f"{ders_kodu} için ana sayfada Save butonu aranıyor...")
                    save_selectors_main = [
                        "//cr-button[contains(text(), 'Save')]",
                        "//button[contains(text(), 'Save')]",
                        "//cr-button[contains(@class, 'action-button')]",
                        "//button[contains(@class, 'action-button')]",
                        "//*[contains(text(), 'Save')]",
                        "//*[contains(text(), 'Kaydet')]",
                        "//button[contains(@aria-label, 'Save')]",
                        "//cr-button[contains(@aria-label, 'Save')]",
                        "//*[@role='button']",
                        "//button",
                        "//cr-button"
                    ]
                    
                    save_clicked = False
                    for selector in save_selectors_main:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, selector)
                            print(f"{ders_kodu} için {selector} ile {len(buttons)} buton bulundu")
                            
                            for button in buttons:
                                try:
                                    button_text = button.text.strip()
                                    button_class = button.get_attribute('class')
                                    print(f"{ders_kodu} için buton: text='{button_text}', class='{button_class}'")
                                    
                                    if 'save' in button_text.lower() or 'kaydet' in button_text.lower():
                                        button.click()
                                        print(f"{ders_kodu} için ana sayfada Save butonuna tıklandı")
                                        save_clicked = True
                                        time.sleep(3)
                                        break
                                except:
                                    continue
                            
                            if save_clicked:
                                break
                                
                        except:
                            continue
                    
                    # Eğer ana sayfada bulunamadıysa iframe'leri kontrol et
                    if not save_clicked:
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        print(f"{ders_kodu} için {len(iframes)} iframe bulundu")
                        
                        for i, iframe in enumerate(iframes):
                            try:
                                self.driver.switch_to.frame(iframe)
                                print(f"{ders_kodu} için iframe {i} içine geçildi")
                                
                                # Save butonunu bul
                                save_selectors = [
                                    "//cr-button[contains(text(), 'Save')]",
                                    "//button[contains(text(), 'Save')]",
                                    "//cr-button[contains(@class, 'action-button')]",
                                    "//button[contains(@class, 'action-button')]",
                                    "//*[contains(text(), 'Save')]",
                                    "//*[contains(text(), 'Kaydet')]",
                                    "//button[contains(@aria-label, 'Save')]",
                                    "//cr-button[contains(@aria-label, 'Save')]",
                                    "//*[@role='button' and contains(text(), 'Save')]",
                                    "//*[@role='button']",
                                    "//button",
                                    "//cr-button"
                                ]
                                
                                for selector in save_selectors:
                                    try:
                                        buttons = self.driver.find_elements(By.XPATH, selector)
                                        print(f"{ders_kodu} için iframe {i} içinde {selector} ile {len(buttons)} buton bulundu")
                                        
                                        for button in buttons:
                                            try:
                                                button_text = button.text.strip()
                                                button_class = button.get_attribute('class')
                                                print(f"{ders_kodu} için iframe {i} buton: text='{button_text}', class='{button_class}'")
                                                
                                                if 'save' in button_text.lower() or 'kaydet' in button_text.lower():
                                                    button.click()
                                                    print(f"{ders_kodu} için iframe {i} içinde Save butonuna tıklandı")
                                                    save_clicked = True
                                                    time.sleep(3)
                                                    break
                                            except:
                                                continue
                                        
                                        if save_clicked:
                                            break
                                            
                                    except:
                                        continue
                                
                                if save_clicked:
                                    break
                                    
                                # iframe'den çık
                                self.driver.switch_to.default_content()
                                
                            except Exception as e:
                                print(f"{ders_kodu} için iframe {i} hatası: {e}")
                                self.driver.switch_to.default_content()
                                continue
                    
                    if not save_clicked:
                        print(f"{ders_kodu} için Save butonu hiçbir yerde bulunamadı")
                        # Alternatif: Enter tuşuna bas
                        try:
                            from selenium.webdriver.common.keys import Keys
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
                            print(f"{ders_kodu} için Enter tuşuna basıldı")
                            time.sleep(2)
                        except:
                            pass
                
                except Exception as e:
                    print(f"{ders_kodu} için Save butonu arama hatası: {e}")
                
                # Ana sayfaya geri dön
                self.driver.switch_to.default_content()
                
                # İndirilen dosyaları kontrol et
                indirilen_dosyalar = [f for f in os.listdir(".") if f.endswith(".pdf")]
                if indirilen_dosyalar:
                    en_son_dosya = max(indirilen_dosyalar, key=os.path.getctime)
                    yeni_yol = os.path.join(hedef_klasor, dosya_adi)
                    os.rename(en_son_dosya, yeni_yol)
                    print(f"{ders_kodu} başarıyla kaydedildi: {yeni_yol}")
                    return True
                else:
                    # Alternatif yöntem: Sayfayı HTML olarak kaydet
                    print(f"{ders_kodu} için PDF bulunamadı, HTML olarak kaydediliyor...")
                    html_path = os.path.join(hedef_klasor, f"{ders_kodu.replace(' ', '')}.html")
                    page_source = self.driver.page_source
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(page_source)
                    print(f"{ders_kodu} HTML olarak kaydedildi: {html_path}")
                    return True
                    
            except TimeoutException:
                print(f"{ders_kodu} için Save butonu bulunamadı")
                return False
            except Exception as e:
                print(f"{ders_kodu} kaydetme hatası: {str(e)}")
                return False
            
        except TimeoutException:
            print(f"{ders_kodu} için element bulunamadı")
            return False
        except Exception as e:
            print(f"{ders_kodu} indirme hatası: {str(e)}")
            return False
    
    def dersleri_indir(self, ders_kodlari):
        basarili_indirilen = 0
        for ders_kodu in ders_kodlari:
            print(f"\n{ders_kodu} indiriliyor...")
            if self.ders_icerigini_indir(ders_kodu):
                basarili_indirilen += 1
            self.driver.back()
            time.sleep(2)
            self.dersler_linkine_tikla()
        print(f"\nToplam {len(ders_kodlari)} ders bulundu, {basarili_indirilen} ders başarıyla indirildi")

    def tum_dersleri_indir(self):
        """Tüm dersleri otomatik olarak indirir"""
        try:
            # Tarayıcıyı başlat
            if not self.tarayici_baslat():
                return False
            
            # OBS sayfasına git
            if not self.obs_sayfasina_git():
                return False
            
            # Dersler linkine tıkla
            if not self.dersler_linkine_tikla():
                return False
            
            # Normal dersleri indir
            print("=== NORMAL DERSLER İNDİRİLİYOR ===")
            normal_ders_kodlari = self.ders_kodlarini_bul()
            
            if normal_ders_kodlari:
                print(f"Normal dersler bulundu: {normal_ders_kodlari}")
                self.dersleri_indir(normal_ders_kodlari)
            else:
                print("Normal ders bulunamadı")
            
            # Gruplu dersleri indir
            print("\n=== GRUPLU DERSLER İNDİRİLİYOR ===")
            try:
                # Gruplu Dersleri Göster butonunu bul ve tıkla
                gruplu_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Gruplu Dersleri Göster')]"))
                )
                gruplu_btn.click()
                print("Gruplu Dersleri Göster butonuna tıklandı")
                time.sleep(3)  # Sayfa yüklenmesi için bekle
                
                # Gruplu ders kodlarını bul
                gruplu_ders_kodlari = self.ders_kodlarini_bul()
                
                if gruplu_ders_kodlari:
                    print(f"Gruplu dersler bulundu: {gruplu_ders_kodlari}")
                    self.dersleri_indir(gruplu_ders_kodlari)
                else:
                    print("Gruplu ders bulunamadı")
                    
            except TimeoutException:
                print("Gruplu Dersleri Göster butonu bulunamadı")
            except Exception as e:
                print(f"Gruplu dersler işleme hatası: {e}")
            
            print("\n=== İNDİRME İŞLEMİ TAMAMLANDI ===")
            return True
            
        except Exception as e:
            print(f"Genel hata: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("Tarayıcı kapatıldı")

def main():
    """Ana fonksiyon"""
    print("Doğuş Üniversitesi OBS Ders İçerik İndirici")
    print("=" * 50)
    
    indirici = IcerikIndirici()
    basari = indirici.tum_dersleri_indir()
    
    if basari:
        print("\nİndirme işlemi tamamlandı!")
    else:
        print("\nİndirme işleminde hata oluştu!")

if __name__ == "__main__":
    main()
