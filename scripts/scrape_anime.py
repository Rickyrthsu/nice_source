import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def run_scraper():
    print("--- [終極無頭瀏覽器模式：深度圖片偵測啟動] ---")
    url = "https://hanime1.me/watch?v=103525"
    print(f"📡 準備解析網址: {url}")
    
    with sync_playwright() as p:
        print("🚀 啟動 Chromium 瀏覽器...")
        # 針對 CI/CD 環境的最佳化參數，避免沙盒權限問題導致崩潰
        browser = p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()
        
        try:
            print("⏳ 載入網頁中...")
            # 將等待條件改為 domcontentloaded，只要 DOM 結構出來就繼續往下走
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # --- 在這裡放入你其他的網頁解析邏輯（例如抓取標題、簡介等） ---
            title = page.title()
            print(f"✅ 成功載入頁面: {title}")
            
            # 依照你的需求，不執行實體圖片下載與儲存，直接輸出標籤讓使用者自行處理
            print("[記得放上圖片，檔案名稱是\"123\"]")
            
        except PlaywrightTimeoutError as e:
            # 捕捉 60 秒超時錯誤
            print(f"❌ 執行發生錯誤: Page.goto: Timeout 60000ms exceeded.")
            print(f"Call log details: {e}")
            print("[記得放上圖片，檔案名稱是\"123\"]")
            
        except Exception as e:
            # 捕捉其他非預期錯誤（例如網站阻擋、網路斷線）
            print(f"❌ 發生其他非預期的錯誤: {e}")
            print("[記得放上圖片，檔案名稱是\"123\"]")
            
        finally:
            browser.close()
            print("🛑 瀏覽器已安全關閉。")

if __name__ == "__main__":
    run_scraper()