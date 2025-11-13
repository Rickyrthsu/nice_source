import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper 
from urllib.parse import urlparse, parse_qs

# --- 輔助函式：爬取動漫 ---
def scrape_anime(url):
    print(f"  [函式: scrape_anime] 開始爬取 {url}...")
    
    # 1. 建立「終極爬蟲」實例
    scraper = cloudscraper.create_scraper()
    
    try:
        # 2. 使用 scraper.get() 騙過 403
        response = scraper.get(url)
        response.raise_for_status() 
        
        # 3. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. 抓取標題和「外部」圖片網址 (不變)
        title_tag = soup.find('meta', property='og:title')
        image_tag = soup.find('meta', property='og:image')
        
        title = title_tag['content'] if title_tag else "找不到標題"
        external_image_url = image_tag['content'] if image_tag else "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        # 5. 【【【 關鍵的「新功能」：抓取標籤！】】】
        print("  [爬蟲第 2.5 步] 正在尋找 <meta name='keywords'>...")
        tags = ["anime"] # 先準備一個預設的
        
        # 尋找 <meta name="keywords" ... >
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        
        # 檢查：(1) 有沒有找到 (2) 它裡面有沒有 'content'
        if keywords_tag and keywords_tag.get('content'):
            keywords_content = keywords_tag.get('content')
            print(f"  [爬蟲第 2.6 步] 成功找到關鍵字: {keywords_content[:50]}...") # 只印出前 50 個字
            
            # 把 "A, B, C" 這種字串，變成 ["A", "B", "C"] 這種列表
            # .strip() 是為了去除多餘的空白
            tags = [tag.strip() for tag in keywords_content.split(',')]
        else:
            print("  [爬蟲警告!] 找不到 <meta name='keywords'> 標籤，使用預設 'anime' 標籤。")
        # ===【【【 新功能結束 】】】===

        
        # 6. 【【【 下載圖片邏輯 (不變) 】】】
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        parsed_url = urlparse(url)
        video_id = parse_qs(parsed_url.query).get('v', [None])[0] 
        image_ext = Path(urlparse(external_image_url).path).suffix
        
        if not video_id: 
            video_id = title.replace(' ', '_').replace('/', '')[:20]
        if not image_ext:
            image_ext = ".jpg"

        our_new_filename = f"anime_{video_id}{image_ext}"
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
        
        print("  [函式: scrape_anime] 爬取成功！")
        return {
            "title": title,
            "imageUrl": str(internal_image_path), 
            "targetUrl": url,
            "tags": tags # 【【【 關鍵！】】】我們現在儲存的是「爬到的」標籤！
        }
    except Exception as e:
        print(f"  [函式: scrape_anime] 爬取動漫 {url} 失敗: {e}")
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
