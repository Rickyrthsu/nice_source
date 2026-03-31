import os
import json
import sys
from pathlib import Path 
from urllib.parse import urlparse, parse_qs
from io import BytesIO 
from bs4 import BeautifulSoup
# 換成更強的抗指紋套件
from curl_cffi import requests as cffi_requests

try:
    from PIL import Image
except ImportError:
    print("❌ 錯誤：找不到 Pillow 庫。")
    sys.exit(1)

def scrape_anime(url):
    print(f"--- [全自動爬蟲與 JPG 轉換模式啟動] ---")
    
    url = url.strip()
    print(f"📡 準備解析網址: {url}")

    if not url.startswith("http"):
        print("❌ 錯誤：請輸入有效的網址 (http/https 開頭)！")
        return None

    # 設定超逼真的瀏覽器 Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://hanime1.me/'
    }

    try:
        # 1. 獲取網頁內容 (使用 curl_cffi 完美模擬 Chrome 120)
        print("🚀 使用高級指紋偽裝繞過 Cloudflare...")
        response = cffi_requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        
        if response.status_code == 403:
            print("❌ 致命錯誤：依然被 403 阻擋。對方的防火牆可能直接封鎖了 GitHub Actions 的機房 IP 網段。")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. 爬取標題
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

        # 3. 爬取封面圖
        external_image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            external_image_url = og_image['content']
        
        if not external_image_url:
            print("❌ 錯誤：無法在網頁中找到封面圖片。")
            return None

        print(f"✅ 成功抓取資訊：\n  - 標題: {title}\n  - 原始圖片: {external_image_url}")

        # 4. 處理圖片儲存路徑
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
        
        # 5. 下載並轉換圖片 (同樣使用 curl_cffi 避開圖片防盜連)
        print(f"💾 正在下載並轉換為 JPG...")
        
        try:
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            img_headers = headers.copy()
            img_headers['Referer'] = domain
            
            img_response = cffi_requests.get(external_image_url, headers=img_headers, impersonate="chrome120", timeout=15)
            
            if img_response.status_code == 200:
                original_image = Image.open(BytesIO(img_response.content))
                
                if original_image.mode != 'RGB':
                    print(f"🔄 圖片模式從 {original_image.mode} 轉換為 RGB...")
                    final_image = original_image.convert('RGB')
                else:
                    final_image = original_image

                final_image.save(internal_image_path, format="JPEG", quality=85, optimize=True)
                print(f"✨ 圖片已轉存為 JPG：{internal_image_path}")
                final_img_path = str(internal_image_path).replace(os.sep, '/')
            else:
                raise Exception(f"圖片下載回傳狀態碼: {img_response.status_code}")

        except Exception as img_e:
            print(f"⚠️ 圖片下載或轉換失敗: {img_e}")
            final_img_path = external_image_url

        # 6. 回傳資料結構
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