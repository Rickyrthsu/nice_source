import os
import json
import requests
import sys
import shutil # 引入 shutil，用於下載圖片

# 【【【 新增 】】】 引入 pathlib，用於處理資料夾路徑
from pathlib import Path 
from bs4 import BeautifulSoup

# --- 輔助函式：爬取 nhentai ---
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code}...")
    print(f"  [爬蟲第 1 步] 正在抓取「API」: https://nhentai.net/api/gallery/{code}")

    try:
        api_url = f"https://nhentai.net/api/gallery/{code}"
        response = requests.get(api_url)
        response.raise_for_status() 
        data = response.json()
        
        media_id = data["media_id"]
        title = data["title"].get("pretty", data["title"].get("english", "N/A")) 
        tags = [tag["name"] for tag in data["tags"]]
        
        # 抓取「縮圖 (thumbnail)」
        thumb_info = data["images"]["thumbnail"]
        thumb_type = 'jpg' if thumb_info["t"] == 'j' else 'png'
        
        # 這是「外部」的圖片網址
        external_image_url = f"https://t.nhentai.net/galleries/{media_id}/thumb.{thumb_type}"
        
        # 這是你「想點進去」的網址
        target_url = f"https://nhentai.net/g/{code}/"
        
        print(f"  [爬蟲第 2 步] API 抓取成功。找到「縮圖」網址: {external_image_url}")

        # === 6.【【【 關鍵大改動：下載並儲存圖片 】】】===
        
        # 我們要建立一個新資料夾 'images' (如果它還不存在)
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True) # exist_ok=True 讓它在資料夾已存在時不會報錯
        
        # 我們的新檔名，用「番號」命名，確保獨一無二
        our_new_filename = f"{code}.{thumb_type}"
        # 我們「內部」的圖片路徑
        internal_image_path = images_dir / our_new_filename # 結果會像 'images/296340.png'
        
        try:
            print(f"  [爬蟲第 3 步] 正在從 {external_image_url} 下載圖片...")
            image_response = requests.get(external_image_url, stream=True)
            image_response.raise_for_status() # 確保下載成功
            
            with open(internal_image_path, 'wb') as f:
                image_response.raw.decode_content = True
                shutil.copyfileobj(image_response.raw, f)
            print(f"  [爬蟲第 4 步] 圖片已成功儲存到: {internal_image_path}")
            
        except Exception as img_e:
            print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
            # 如果下載失敗，我們還是用「預設圖示」
            internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        # === 下載完畢 ===

        # 7. 組合我們要「儲存」的資料格式
        result = {
            "title": title,
            "code": code,
            "imageUrl": str(internal_image_path), # 儲存「我們自己的」內部路徑 (e.g., "images/296340.png")
            "targetUrl": target_url,       
            "tags": tags
        }
        return result

    except Exception as e:
        print(f"  [函式: scrape_comic] 爬取漫畫 {code} 失敗 (API 錯誤): {e}")
        return None

# --- 輔助函式：爬取影片 (目前是範本，不動) ---
# ... (scrape_video 函式保持不變) ...
def scrape_video(code):
    print(f"  [函式: scrape_video] 影片 {code} 的爬蟲尚未實作，使用範本資料")
    return {
        "title": f"影片範本: {code}",
        "code": code,
        "imageUrl": "https://via.placeholder.com/200x250.png?text=Video+Placeholder",
        "targetUrl": "#",
        "tags": ["video", "placeholder"]
    }

# --- 輔助函式：爬取動 animé (通用連結，不動) ---
# ... (scrape_anime 函式保持不變) ...
def scrape_anime(url):
    print(f"  [函式: scrape_anime] 開始爬取 {url}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('meta', property='og:title')
        image_tag = soup.find('meta', property='og:image')
        
        title = title_tag['content'] if title_tag else "找不到標題"
        image_url = image_tag['content'] if image_tag else "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        print("  [函式: scrape_anime] 爬取成功！")
        return {
            "title": title,
            "imageUrl": image_url,
            "targetUrl": url,
            "tags": ["anime"]
        }
    except Exception as e:
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