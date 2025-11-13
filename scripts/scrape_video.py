import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper 
from urllib.parse import urlparse, quote 

# --- 輔助函式：爬取影片 (MissAV) ---
def scrape_video(code):
    print(f"  [函式: scrape_video] 開始爬取 {code}...")
    
    # 1. 格式化你的輸入
    formatted_code = code.replace(" ", "-").upper()
    encoded_code = quote(formatted_code)
    
    # 2. 組合 MissAV 的「搜尋」網址
    base_url = "https://missav.ws" # 我們用它來「檢查」，而不是「相加」
    search_url = f"{base_url}/search/{encoded_code}"
    print(f"  [爬蟲第 1 步] 正在用 Cloudscraper 抓取「搜尋頁」: {search_url}")

    # 3. 建立「終極爬蟲」實例
    scraper = cloudscraper.create_scraper()
    
    try:
        # 4. 使用 scraper.get() 騙過 403
        response = scraper.get(search_url)
        response.raise_for_status() 
        
        # 5. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 6. 在 HTML 中「尋找」【第一筆】搜尋結果
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            # === (Google Fallback 邏輯 - 保持不變) ===
            print(f"  [爬蟲警告!] 在 MissAV 上找不到番號 {formatted_code}。")
            print(f"  [爬蟲警告!] 正在執行你的「Google Fallback」計畫...")
            return {
                "title": f"在 Google 搜尋: {formatted_code}",
                "code": formatted_code,
                "imageUrl": "https://via.placeholder.com/200x250.png?text=Not+Found", 
                "targetUrl": f"https://www.google.com/search?q=missav+{encoded_code}", 
                "tags": ["video", "not-found"]
            }

        print("  [爬蟲第 2 步] 成功在 HTML 中找到第一筆結果。")
        
        # 7. 【【【 關鍵 Bug 修正區 】】】
        link_tag = first_result.find('a')
        img_tag = first_result.find('img')

        if not link_tag or not img_tag:
            print("  [爬蟲錯誤!] 找到 thumbnail，但找不到 <a> 或 <img> 標籤。")
            return None

        # 1. 【Bug 1 修正 (URL)】
        href = link_tag.get('href')
        if not href:
             print("  [爬蟲錯誤!] <a> 標籤沒有 'href'。")
             return None
        
        # 檢查 href 是不是「已經」是完整網址了
        if href.startswith('http'):
            target_url = href # 100% 正確，直接使用
        else:
            target_url = f"{base_url}{href}" # 它是相對路徑，補上 base_url

        # 2. 【Bug 2 修正 (Image)】
        #    我們「優先」抓 'data-src'，如果「抓不到」，才改抓 'src'
        external_image_url = img_tag.get('data-src', img_tag.get('src'))
        
        if not external_image_url:
            print("  [爬蟲警告!] <img> 標籤沒有 'src' 或 'data-src'，使用預設圖片。")
            external_image_url = "https://via.placeholder.com/200x250.png?text=Image+Missing"

        # 3. (不變) 安全地取得 title
        title = img_tag.get('title', f"影片: {formatted_code}") 
        # === 修正完畢 ===
        
        tags = ["video"] 
        
        # 8. 下載圖片邏輯 (跟漫畫一樣)
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        image_ext = Path(urlparse(external_image_url).path).suffix
        if not image_ext or image_ext == ".gif" or "data:image" in external_image_url:
            # 如果還是抓到 data:image (代表 data-src 也沒有)，就用預設
            image_ext = ".jpg"
            internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        else:
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
                internal_image_path = str(internal_image_path) # 轉成字串
                
            except Exception as img_e:
                print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
                internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        print(f"  [函式: scrape_video] 爬取 {formatted_code} 成功！")
        return {
            "title": title,
            "code": formatted_code,
            "imageUrl": internal_image_path, # 儲存「內部」路徑 (或預設圖)
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
