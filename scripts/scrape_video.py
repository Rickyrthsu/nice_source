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
    
    # 1. 格式化你的輸入
    formatted_code = code.replace(" ", "-").upper()
    encoded_code = quote(formatted_code)
    
    # 2. 【【【 關鍵修正 #1：更換網域！】】】
    #    舊的 (已死): missav.com
    #    新的 (正確): missav.ws
    base_url = "https://missav.ws"
    search_url = f"{base_url}/search/{encoded_code}"
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
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            print(f"  [爬蟲警告!] 在 MissAV 上找不到番號 {formatted_code} 的任何結果。")
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
        
        # 8. 【【【 關鍵修正 #2：補上完整網域！】】】
        #    link_tag['href'] 只會是 "/dm28/ssni-123" (相對路徑)
        #    我們必須補上 base_url 才會變成完整連結
        target_url = f"{base_url}{link_tag['href']}"
        
        title = img_tag['title'] 
        external_image_url = img_tag['src']
        
        tags = ["video"] 
        
        # 9. 下載圖片邏輯 (跟漫畫一樣)
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        image_ext = Path(urlparse(external_image_url).path).suffix
        if not image_ext:
            image_ext = ".jpg" 

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
            "imageUrl": str(internal_image_path), # 儲存「內部」路徑
            "targetUrl": target_url, # 儲存「完整」網址
            "tags": tags
        }
    except Exception as e:
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
