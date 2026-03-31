import os
import json
import sys
from pathlib import Path 
from urllib.parse import urlparse, parse_qs
from io import BytesIO # 用於在記憶體中處理圖片數據
from bs4 import BeautifulSoup
import cloudscraper
# Pillow 庫
try:
    from PIL import Image
except ImportError:
    print("❌ 錯誤：找不到 Pillow 庫。請執行 'pip install Pillow'")
    sys.exit(1)

def scrape_anime(url):
    print(f"--- [全自動爬蟲與 JPG 轉換模式啟動] ---")
    
    url = url.strip()
    print(f"📡 準備解析網址: {url}")

    if not url.startswith("http"):
        print("❌ 錯誤：請輸入有效的網址 (http/https 開頭)！")
        return None

    # 初始化 cloudscraper (模擬瀏覽器避開 Cloudflare)
    scraper = cloudscraper.create_scraper()
    
    try:
        # 1. 獲取網頁內容
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. 爬取標題 (優先找 Open Graph 的 og:title)
        title = ""
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content']
        else:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.text.strip()
        
        # 清理標題後綴 (可依需求調整)
        title = title.replace(" - Hanime1.me", "").strip()
        if not title:
            title = "Unknown Anime Title"

        # 3. 爬取封面圖 (優先找 og:image)
        external_image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            external_image_url = og_image['content']
        
        if not external_image_url:
            print("❌ 錯誤：無法在網頁中找到封面圖片 (og:image)。")
            return None

        print(f"✅ 成功抓取資訊：\n  - 標題: {title}\n  - 原始圖片: {external_image_url}")

        # 4. 處理圖片儲存路徑與檔名
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # 解析網址以產生唯一的安全檔名
        parsed_url = urlparse(url)
        video_id_list = parse_qs(parsed_url.query).get('v') 
        # 如果是 hanime1.me?v=xxx 格式，用 xxx 做檔名，否則用網址路徑最後一段
        video_id = video_id_list[0] if video_id_list else Path(parsed_url.path).name
        if not video_id:
            # 防呆：如果完全解析不到 ID，用網址的 hash 值
            video_id = "auto_" + str(hash(url))[-8:]
        
        # 清理檔名，只保留數字、字母與底線/連字號
        safe_video_id = "".join([c for c in video_id if c.isalnum() or c in ['-', '_']]).strip()
        
        # --- [重點更新] 強制將檔名設為 .jpg ---
        image_filename = f"anime_{safe_video_id}.jpg"
        internal_image_path = images_dir / image_filename
        
        # 5. 下載並轉換圖片 (JPG 轉換邏輯)
        print(f"💾 正在下載並轉換為 JPG...")
        
        try:
            # A. 下載原始圖片數據到記憶體 (不直接存檔)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': domain
            }
            img_response = scraper.get(external_image_url, headers=headers, stream=False, timeout=15)
            img_response.raise_for_status()
            
            # B. 使用 Pillow 讀取記憶體中的數據
            original_image = Image.open(BytesIO(img_response.content))
            
            # C. 重要：轉換為 RGB 模式！
            # 這是轉 JPG 的必要步驟，可以處理透明通道 (WEBP/PNG with Alpha) 避免錯誤。
            if original_image.mode != 'RGB':
                print(f"🔄 圖片模式從 {original_image.mode} 轉換為 RGB...")
                final_image = original_image.convert('RGB')
            else:
                final_image = original_image

            # D. 儲存為 JPG (設定壓縮品質為 85，平衡大小與畫質)
            final_image.save(internal_image_path, format="JPEG", quality=85, optimize=True)
            print(f"✨ 圖片已轉存為 JPG：{internal_image_path}")
            
            # 確保寫入 JSON 的路徑符合網路標準的正斜線
            final_img_path = str(internal_image_path).replace(os.sep, '/')

        except Exception as img_e:
            print(f"⚠️ 圖片下載或 JPG 轉換失敗: {img_e}")
            # [回退機制] 如果 Pillow 轉換掛掉，直接嘗試原始下載 (不做轉換) 作為備案
            try:
                # 回復使用原始副檔名
                fallback_filename = f"anime_{safe_video_id}{Path(external_image_url).suffix}"
                fallback_path = images_dir / fallback_filename
                
                # 重新下載流並儲存
                import shutil
                r = scraper.get(external_image_url, headers=headers, stream=True, timeout=15)
                with open(fallback_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                print(f"⚠️ 已回退到原始檔案儲存：{fallback_path}")
                final_img_path = str(fallback_path).replace(os.sep, '/')
            except Exception as fallback_e:
                print(f"❌ 回退下載也失敗：{fallback_e}，使用原始外部網址。")
                final_img_path = external_image_url

        # 6. 回傳資料結構 (供 JSON 使用)
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

def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到 GitHub Action 輸入值 (COLLECTION_TYPE/COLLECTION_VALUE)")
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    new_entry = scrape_anime(cvalue)
    
    if not new_entry:
        # 爬取失敗時，讓 Action 執行失敗以通知使用者
        sys.exit(1) 
        
    # 設定類別 (漫畫 -> comic, 影片 -> video, 動漫 -> anime)
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime', 'Porn': 'video' }
    new_entry['category'] = category_map.get(ctype, 'anime')

    # 讀取並更新 data.json
    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
          try:
            data = json.load(f)
          except json.JSONDecodeError:
            # 防呆：如果 json 壞掉，初始化一個新的清單
            data = []
    except FileNotFoundError:
        data = []
    
    # 新資料放在最前面
    data.insert(0, new_entry)
    
    # 寫回 data.json
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 成功將資料（圖片路徑：{new_entry['imageUrl']}）新增到 data.json！")

if __name__ == "__main__":
    main()