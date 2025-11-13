import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup

# 【【【 新增神器！】】】
import cloudscraper

# --- 輔助函式：爬取 nhentai ---
# (這個函式 100% 不用動，因為 nhentai 的 API 沒那麼機車)
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code}...")
    # ... (程式碼 100% 保持不變) ...
    try:
        api_url = f"https://nhentai.net/api/gallery/{code}"
        response = requests.get(api_url)
        response.raise_for_status() 
        data = response.json()
        
        media_id = data["media_id"]
        title = data["title"].get("pretty", data["title"].get("english", "N/A")) 
        tags = [tag["name"] for tag in data["tags"]]
        
        thumb_info = data["images"]["thumbnail"]
        thumb_type = 'jpg' if thumb_info["t"] == 'j' else 'png'
        
        external_image_url = f"https://t.nhentai.net/galleries/{media_id}/thumb.{thumb_type}"
        target_url = f"https://nhentai.net/g/{code}/"
        
        print(f"  [爬蟲第 2 步] API 抓取成功。找到「縮圖」網址: {external_image_url}")

        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True) 
        
        our_new_filename = f"{code}.{thumb_type}"
        internal_image_path = images_dir / our_new_filename
        
        try:
            print(f"  [爬蟲第 3 步] 正在從 {external_image_url} 下載圖片...")
            image_response = requests.get(external_image_url, stream=True)
            image_response.raise_for_status() 
            
            with open(internal_image_path, 'wb') as f:
                image_response.raw.decode_content = True
                shutil.copyfileobj(image_response.raw, f)
            print(f"  [爬蟲第 4 步] 圖片已成功儲存到: {internal_image_path}")
            
        except Exception as img_e:
            print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
            internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"

        result = {
            "title": title,
            "code": code,
            "imageUrl": str(internal_image_path), 
            "targetUrl": target_url,       
            "tags": tags
        }
        return result

    except Exception as e:
        print(f"  [函式: scrape_comic] 爬取漫畫 {code} 失敗 (API 錯誤): {e}")
        return None

# --- 輔助函式：爬取影片 (目前是範本，不動) ---
def scrape_video(code):
    print(f"  [函式: scrape_video] 影片 {code} 的爬蟲尚未實作，使用範本資料")
    # ... (程式碼 100% 保持不變) ...
    return {
        "title": f"影片範本: {code}",
        "code": code,
        "imageUrl": "https://via.placeholder.com/200x250.png?text=Video+Placeholder",
        "targetUrl": "#",
        "tags": ["video", "placeholder"]
    }

# ---【【【 關鍵大修正：scrape_anime 函式 】】】---
def scrape_anime(url):
    print(f"  [函式: scrape_anime] 開始爬取 {url}...")
    
    # 1. 建立一個「終極爬蟲」實例
    #    (它會自動偽裝成瀏覽器)
    scraper = cloudscraper.create_scraper()
    
    try:
        # 2. 【【【 關鍵！】】】
        #    我們不再用 requests.get()
        #    我們改用 scraper.get()
        response = scraper.get(url)
        
        response.raise_for_status() # 確保請求成功 (不是 403, 404, 500)
        
        # 3. (不變) 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. (不變) 抓取標題和圖片
        title_tag = soup.find('meta', property='og:title')
        image_tag = soup.find('meta', property='og:image')
        
        title = title_tag['content'] if title_tag else "找不到標題"
        image_url = image_tag['content'] if image_tag else "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        print("  [函式: scrape_anime] 爬取成功！")
        return {
            "title": title,
            "imageUrl": image_url, # 注意：這裡我們還是用「外部」連結
            "targetUrl": url,
            "tags": ["anime"]
        }
    except Exception as e:
        # 如果連 cloudscraper 都失敗，我們就會在這裡看到錯誤
        print(f"  [函式: scrape_anime] 爬取動漫 {url} 失敗: {e}")
        return None

# --- 主程式 (保持不變) ---
def main():
    
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到類別或輸入值 (COLLECTION_TYPE or COLLECTION_VALUE)")
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 值={cvalue}")

    new_entry = None
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime' }
    
    if ctype == '漫畫':
        new_entry = scrape_comic(cvalue)
    elif ctype == '影片':
        new_entry = scrape_video(cvalue)
    elif ctype == '動漫':
        new_entry = scrape_anime(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) 
        
    new_entry['category'] = category_map.get(ctype, 'unknown')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"警告：找不到 {data_file}，將建立一個新的。")
        data = []
    
    data.insert(0, new_entry)
    
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"--- [GitHub Actions 執行完畢] ---")
        print(f"✅ 成功新增資料到 data.json！")
        
    except Exception as e:
        print(f"❌ 寫入 data.json 失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()