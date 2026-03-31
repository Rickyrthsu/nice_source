import os
import json
import sys
from pathlib import Path 
from urllib.parse import urlparse, parse_qs
from io import BytesIO 
from bs4 import BeautifulSoup

try:
    from PIL import Image
except ImportError:
    print("❌ 錯誤：找不到 Pillow 庫。")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
except ImportError:
    print("❌ 錯誤：找不到 Playwright。請確認 YAML 有正確安裝 playwright 與 playwright-stealth。")
    sys.exit(1)

def scrape_anime(url):
    print(f"--- [終極無頭瀏覽器 + 隱形斗篷模式啟動] ---")
    
    url = url.strip()
    print(f"📡 準備解析網址: {url}")

    if not url.startswith("http"):
        print("❌ 錯誤：請輸入有效的網址 (http/https 開頭)！")
        return None

    # 啟動 Playwright
    with sync_playwright() as p:
        print("🚀 啟動 Chromium 瀏覽器...")
        # 設定為無頭模式，並加入繞過沙盒的參數 (GitHub Actions 必備)
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        
        # 建立一個擬真的瀏覽器上下文
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-TW',
            timezone_id='Asia/Taipei'
        )
        
        page = context.new_page()
        
        # 披上隱形斗篷 (消除 WebDriver 標記、偽裝 WebGL 等)
        print("🥷 披上 playwright-stealth 隱形斗篷...")
        stealth_sync(page)

        try:
            print("⏳ 進入網站並等待 Cloudflare 盾牌驗證 (可能需要幾秒鐘)...")
            # 載入網頁，等待網路活動靜止
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # 強制等待 3 秒，讓 Cloudflare 的 JS 挑戰有時間執行完畢
            page.wait_for_timeout(3000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 檢查是否還是被 403 擋住
            if "403 Forbidden" in html or "Cloudflare" in page.title():
                print("❌ 致命錯誤：依然被 Cloudflare 阻擋。對方的防火牆已經直接封鎖了 GitHub 的整個 ASN (機房網段)。")
                return None

            # --- 2. 爬取標題 ---
            title = ""
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content']
            else:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.strip()
            
            title = title.replace(" - Hanime1.me", "").strip()
            if not title:
                title = "Unknown Anime Title"

            # --- 3. 爬取封面圖 ---
            external_image_url = ""
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                external_image_url = og_image['content']
            
            if not external_image_url:
                print("❌ 錯誤：無法在網頁中找到封面圖片。")
                return None

            print(f"✅ 成功抓取資訊：\n  - 標題: {title}\n  - 原始圖片: {external_image_url}")

            # --- 4. 處理圖片儲存路徑 ---
            images_dir = Path('images')
            images_dir.mkdir(exist_ok=True)
            
            parsed_url = urlparse(url)
            video_id_list = parse_qs(parsed_url.query).get('v') 
            video_id = video_id_list[0] if video_id_list else Path(parsed_url.path).name
            if not video_id:
                video_id = "auto_" + str(hash(url))[-8:]
            
            safe_video_id = "".join([c for c in video_id if c.isalnum() or c in ['-', '_']]).strip()
            image_filename = f"anime_{safe_video_id}.jpg"
            internal_image_path = images_dir / image_filename
            
            # --- 5. 下載並轉換圖片 (使用同一個已通過驗證的瀏覽器通道) ---
            print(f"💾 正在下載並轉換為 JPG...")
            try:
                # 這裡直接用 Playwright 的 API 抓圖，帶上 Referer，完全模擬正常瀏覽行為
                img_response = context.request.get(external_image_url, headers={'Referer': url})
                
                if img_response.ok:
                    img_buffer = img_response.body()
                    original_image = Image.open(BytesIO(img_buffer))
                    
                    if original_image.mode != 'RGB':
                        print(f"🔄 圖片模式從 {original_image.mode} 轉換為 RGB...")
                        final_image = original_image.convert('RGB')
                    else:
                        final_image = original_image

                    final_image.save(internal_image_path, format="JPEG", quality=85, optimize=True)
                    print(f"✨ 圖片已轉存為 JPG：{internal_image_path}")
                    final_img_path = str(internal_image_path).replace(os.sep, '/')
                else:
                    raise Exception(f"圖片下載回傳狀態碼: {img_response.status}")

            except Exception as img_e:
                print(f"⚠️ 圖片下載或轉換失敗: {img_e}")
                final_img_path = external_image_url

            return {
                "title": title,
                "imageUrl": final_img_path, 
                "targetUrl": url,
                "tags": ["anime"], 
                "details": {}
            }

        except Exception as e:
            print(f"❌ 網頁解析失敗: {e}")
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
        
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime', 'Porn': 'video' }
    new_entry['category'] = category_map.get(ctype, 'anime')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
          try:
            data = json.load(f)
          except json.JSONDecodeError:
            data = []
    except FileNotFoundError:
        data = []
    
    data.insert(0, new_entry)
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 成功將資料（圖片路徑：{new_entry['imageUrl']}）新增到 data.json！")

if __name__ == "__main__":
    main()