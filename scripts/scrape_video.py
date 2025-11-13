import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper # 影片爬蟲也需要「終極神器」
from urllib.parse import urlparse, quote # 引入 quote 來處理 URL 編碼

# --- 輔助函式：爬取影片 (MissAV) ---
def scrape_video(code):
    print(f"  [函式: scrape_video] 開始爬取 {code}...")
    
    # 1. 【【【 關鍵！】】】 格式化你的輸入
    #    例如 "FC2 PPV 3498155" -> "FC2-PPV-3498155"
    formatted_code = code.replace(" ", "-").upper()
    
    # 對番號進行 URL 編碼，確保網址正確
    encoded_code = quote(formatted_code)
    
    # 2. 組合 MissAV 的「搜尋」網址
    search_url = f"https://missav.com/search/{encoded_code}"
    print(f"  [爬蟲第 1 步] 正在用 Cloudscraper 抓取「搜尋頁」: {search_url}")

    # 3. 建立「終極爬蟲」實例
    scraper = cloudscraper.create_scraper()
    
    try:
        # 4. 使用 scraper.get() 騙過 403
        response = scraper.get(search_url)
        response.raise_for_status() # 確保請求成功 (不是 403, 404, 500)
        
        # 5. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 6. 在 HTML 中「尋找」【第一筆】搜尋結果
        #    (MissAV 的卡片 class 是 'thumbnail')
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            print(f"  [爬蟲警告!] 在 MissAV 上找不到番號 {formatted_code} 的任何結果。")
            # 返回一個「找不到」的範本
            return {
                "title": f"找不到: {formatted_code}",
                "code": formatted_code,
                "imageUrl": "https://via.placeholder.com/200x250.png?text=Not+Found",
                "targetUrl": search_url, # 連結到搜尋頁，方便你手動確認
                "tags": ["video", "not-found"]
            }

        print("  [爬蟲第 2 步] 成功在 HTML 中找到第一筆結果。")
        
        # 7. 從第一筆結果中「挖出」資料
        link_tag = first_result.find('a')
        img_tag = first_result.find('img')
        
        target_url = link_tag['href']
        # 標題在 <img> 標籤的 'title' 屬性裡
        title = img_tag['title'] 
        # 封面圖在 <img> 標籤的 'src' 屬性裡
        external_image_url = img_tag['src']
        
        # 8. 抓取標籤 (MissAV 的標籤在卡片「外面」，解析很麻煩，我們先省略)
        tags = ["video"] # 先給一個預設標籤
        
        # 9. 【【【 下載圖片邏輯 (跟漫畫一樣) 】】】
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # 取得圖片的副檔名 (例如 .jpg)
        image_ext = Path(urlparse(external_image_url).path).suffix
        if not image_ext:
            image_ext = ".jpg" # 預設 .jpg

        # 我們的新檔名，例如 "video_SSNI-123.jpg"
        our_new_filename = f"video_{formatted_code}{image_ext}"
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
        # === 下載完畢 ===
        
        print(f"  [函式: scrape_video] 爬取 {formatted_code} 成功！")
        return {
            "title": title,
            "code": formatted_code,
            "imageUrl": str(internal_image_path), # 【【【 關鍵！】】】我們儲存「內部」路徑
            "targetUrl": target_url,
            "tags": tags
        }
    except Exception as e:
        # 如果連 cloudscraper 都失敗，我們就會在這裡看到錯誤
        print(f"  [函式: scrape_video] 爬取影片 {code} 失敗: {e}")
        return None

# --- 主程式 (所有腳本共用的，100% 不用動) ---
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
    
    # 這是這個檔案「唯一」的任務
    new_entry = scrape_video(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) 
        
    new_entry['category'] = category_map.get(ctype, 'unknown')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
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
