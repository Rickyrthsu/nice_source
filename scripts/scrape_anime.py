import os
import json
import sys
from pathlib import Path 
from urllib.parse import urlparse, parse_qs
from io import BytesIO 
from bs4 import BeautifulSoup

try:
    from PIL import Image
except ImportError as e:
    print(f"❌ 錯誤：無法載入 Pillow 庫。詳細資訊: {e}")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"❌ 錯誤：無法載入 Playwright。詳細資訊: {e}")
    sys.exit(1)

try:
    from playwright_stealth import Stealth
except ImportError as e:
    print(f"❌ 錯誤：無法載入 playwright-stealth。詳細資訊: {e}")
    sys.exit(1)

def scrape_anime(url):
    print(f"--- [終極無頭瀏覽器模式：深度圖片偵測啟動] ---")
    
    url = url.strip()
    print(f"📡 準備解析網址: {url}")

    if not url.startswith("http"):
        print("❌ 錯誤：請輸入有效的網址！")
        return None

    with sync_playwright() as p:
        print("🚀 啟動 Chromium 瀏覽器...")
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        stealth = Stealth()
        stealth.apply_stealth_sync(context)
        page = context.new_page()

        try:
            print("⏳ 載入網頁中...")
            # 增加超時時間，並等待網絡相對空閒
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000) # 給予額外緩衝處理 JS

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # --- [強化版圖片偵測邏輯] ---
            external_image_url = ""
            
            # 策略 1: 尋找 Meta OG Image
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                external_image_url = og_image['content']
                print(f"🎯 透過 og:image 找到: {external_image_url}")

            # 策略 2: 尋找 link image_src
            if not external_image_url:
                link_image = soup.find('link', rel='image_src')
                if link_image and link_image.get('href'):
                    external_image_url = link_image['href']
                    print(f"🎯 透過 image_src 找到: {external_image_url}")

            # 策略 3: 尋找所有包含 hembed.com 的 img 標籤 (針對 hanime1)
            if not external_image_url:
                print("🔍 嘗試深度搜尋網頁圖片標籤...")
                imgs = soup.find_all('img')
                for img in imgs:
                    src = img.get('src') or img.get('data-src') or ""
                    if 'hembed.com/image' in src:
                        external_image_url = src
                        print(f"🎯 透過深度搜尋找到標籤圖片: {external_image_url}")
                        break

            if not external_image_url:
                print("❌ 錯誤：無法在網頁中找到任何封面圖片。")
                # 這裡印出標題幫助除錯，看是否連網頁都進不去
                print(f"目前網頁標題為: {page.title()}")
                return None

            # --- 處理標題 ---
            title = ""
            og_title = soup.find('meta', property='og:title')
            title = og_title['content'] if og_title else page.title()
            title = title.replace(" - Hanime1.me", "").strip()

            # --- 下載與轉換 ---
            images_dir = Path('images')
            images_dir.mkdir(exist_ok=True)
            
            # 提取 ID 產生檔名
            parsed_url = urlparse(url)
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            if not video_id:
                video_id = "auto_" + str(hash(url))[-8:]
            
            safe_video_id = "".join([c for c in video_id if c.isalnum() or c in ['-', '_']]).strip()
            image_filename = f"anime_{safe_video_id}.jpg"
            internal_image_path = images_dir / image_filename
            
            print(f"💾 正在下載並轉換 JPG...")
            # 帶上 Referer 下載
            img_response = context.request.get(external_image_url, headers={'Referer': url})
            
            if img_response.ok:
                img_buffer = img_response.body()
                img = Image.open(BytesIO(img_buffer))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(internal_image_path, format="JPEG", quality=85, optimize=True)
                print(f"✨ 儲存成功：{internal_image_path}")
                final_img_path = str(internal_image_path).replace(os.sep, '/')
            else:
                print(f"⚠️ 圖片下載失敗，狀態碼: {img_response.status}")
                final_img_path = external_image_url

            return {
                "title": title,
                "imageUrl": final_img_path, 
                "targetUrl": url,
                "tags": ["anime"], 
                "details": {}
            }

        except Exception as e:
            print(f"❌ 執行發生錯誤: {e}")
            return None
        finally:
            browser.close()

def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    if not ctype or not cvalue:
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    new_entry = scrape_anime(cvalue)
    
    if not new_entry:
        sys.exit(1) 
        
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime' }
    new_entry['category'] = category_map.get(ctype, 'anime')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = []
    
    data.insert(0, new_entry)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 成功更新資料庫！")

if __name__ == "__main__":
    main()