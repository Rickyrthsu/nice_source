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
    
    # 【【【 Bug 修正！】】】
    if not url.startswith('http'):
         print(f"  [爬蟲警告!] 你輸入的是 番號，但類別選「動漫」。")
         print(f"  [爬蟲警告!] 正在執行「Google Fallback」...")
         return {
            "title": f"類別錯誤: {url}",
            "code": "Error",
            "imageUrl": "https://via.placeholder.com/200x250.png?text=Wrong+Category", 
            "targetUrl": f"https://www.google.com/search?q={quote(url)}", 
            "tags": ["anime", "error"],
            "details": {} 
         }

    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.find('meta', property='og:title')
        image_tag = soup.find('meta', property='og:image')
        
        title = title_tag['content'] if title_tag else "找不到標題"
        external_image_url = image_tag['content'] if image_tag else "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        print("  [爬蟲第 2.5 步] 正在尋找 <meta name='keywords'>...")
        tags = ["anime"] 
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        
        if keywords_tag and keywords_tag.get('content'):
            keywords_content = keywords_tag.get('content')
            print(f"  [爬蟲第 2.6 步] 成功找到關鍵字: {keywords_content[:50]}...")
            tags = [tag.strip() for tag in keywords_content.split(',')]
        else:
            print("  [爬蟲警告!] 找不到 <meta name='keywords'> 標籤，使用預設 'anime' 標籤。")

        
        # 6. 【【【 下載圖片邏輯 】】】
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # === 【【【 這就是「錯誤」的地方！】】】 ===
        parsed_url = urlparse(url)
        video_id_list = parse_qs(parsed_url.query).get('v') 
        
        # === 【【【 我「忘記」加的「下一行」在這裡！】】】 ===
        if video_id_list: # 如果 video_id_list 不是 None (代表 ?v= 存在)
            video_id = video_id_list[0] # 我們才安全地拿 [0]
        else:
            video_id = None # 找不到
        # === 【【【 修正完畢 】】】 ===
            
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
            internal_image_path = str(internal_image_path) # 轉成字串
            
        except Exception as img_e:
            print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
            internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        # === 下載完畢 ===
        
        print("  [函式: scrape_anime] 爬取成功！")
        return {
            "title": title,
            "imageUrl": internal_image_path, 
            "targetUrl": url,
            "tags": tags, 
            "details": {} # 動漫沒有詳細資料
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