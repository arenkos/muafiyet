from playwright.sync_api import sync_playwright
import os
import re
import time

def normalize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', '_'))

def tum_dersleri_pdf_kaydet(url, pdf_klasoru):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        os.makedirs(pdf_klasoru, exist_ok=True)

        # Sol menüden 'Dersler' linkine tıkla
        print("Sol menüde 'Dersler' linki aranıyor...")
        dersler_link = page.query_selector("a.nav-link:has-text('Dersler')")
        if not dersler_link:
            print("Dersler linki bulunamadı!")
            browser.close()
            return
        dersler_link.click()
        print("'Dersler' linkine tıklandı.")
        page.wait_for_timeout(3000)

        # Iframe'i bul
        print("Sayfadaki iframe'ler aranıyor...")
        iframe = None
        for f in page.frames:
            if f.url != page.url and "showPac" in f.url:
                iframe = f
                break
        if not iframe:
            try:
                iframe_element = page.query_selector("iframe#IFRAME1")
                if iframe_element:
                    iframe = iframe_element.content_frame()
            except:
                pass
        if not iframe:
            print("Dersler iframe'i bulunamadı!")
            browser.close()
            return
        print("Dersler iframe'ine geçildi.")

        # Ders kodu linklerini bul
        ders_linkleri = iframe.query_selector_all("a[id^='grdBolognaDersler_btnDersKod_']")
        print(f"Toplam {len(ders_linkleri)} ders bulundu.")
        
        for i, link in enumerate(ders_linkleri):
            try:
                ders_kodu = link.inner_text().strip()
                print(f"Ders {i+1}/{len(ders_linkleri)}: {ders_kodu}")
                
                # Her ders için iframe'i yeniden bul
                iframe = None
                for f in page.frames:
                    if f.url != page.url and "showPac" in f.url:
                        iframe = f
                        break
                if not iframe:
                    try:
                        iframe_element = page.query_selector("iframe#IFRAME1")
                        if iframe_element:
                            iframe = iframe_element.content_frame()
                    except:
                        pass
                
                if not iframe:
                    print(f"İframe bulunamadı, {ders_kodu} atlanıyor...")
                    continue
                
                # Ders linkini yeniden bul
                ders_linkleri_guncel = iframe.query_selector_all("a[id^='grdBolognaDersler_btnDersKod_']")
                if i < len(ders_linkleri_guncel):
                    link = ders_linkleri_guncel[i]
                else:
                    print(f"Link bulunamadı, {ders_kodu} atlanıyor...")
                    continue
                
                # Derse tıkla
                iframe.click(f"a[id^='grdBolognaDersler_btnDersKod_']:nth-child({i+1})")
                iframe.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # PDF kaydet
                dosya_adi = os.path.join(pdf_klasoru, f"{normalize_filename(ders_kodu)}.pdf")
                iframe.pdf(path=dosya_adi, format="A4")
                print(f"PDF kaydedildi: {dosya_adi}")
                
                # Geri dön
                iframe.go_back()
                iframe.wait_for_load_state("networkidle")
                time.sleep(1)
                
            except Exception as e:
                print(f"Hata: {ders_kodu} işlenirken hata oluştu: {str(e)}")
                continue
        
        browser.close()

if __name__ == "__main__":
    url = "https://obs.dogus.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=3&curSunit=76"
    pdf_klasoru = "icerikler/Doğuş Üniversitesi/Yazılım Mühendisliği"
    tum_dersleri_pdf_kaydet(url, pdf_klasoru) 