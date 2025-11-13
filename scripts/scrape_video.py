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
    
    # 2. 組合 MissAV 的「搜尋」網址
    base_url = "https://missav.ws"
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
        
        # 6. 【【【 關鍵修正 #1：加入「Google Fallback」邏輯 】】】
        #    在 HTML 中「尋找」【第一筆】搜尋結果
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            # === 如果「真的」找不到任何結果 ===
            print(f"  [爬蟲警告!] 在 MissAV 上找不到番號 {formatted_code}。")
            print(f"  [爬蟲警告!] 正在執行你的「Google Fallback」計畫...")

            # 我們就回傳一個「Google 搜尋」的卡片
            return {
                "title": f"在 Google 搜尋: {formatted_code}", # 標題
                "code": formatted_code,
                "imageUrl": "https://via.placeholder.com/200x250.png?text=Not+Found", # 預設圖片
                "targetUrl": f"https://www.google.com/search?q=missav+{encoded_code}", # 【【【 你的要求！】】】
                "tags": ["video", "not-found"]
            }

        # === 如果有找到結果，我們就繼續 ===
        print("  [爬蟲第 2 步] 成功在 HTML 中找到第一筆結果。")
        
        # 7. 【【【 關鍵修正 #2：用「安全」的方式解析 】】】
        link_tag = first_result.find('a')
        img_tag = first_result.find('img')

        # 檢查標籤是否存在
        if not link_tag or not img_tag:
            print("  [爬蟲錯誤!] 找到 thumbnail，但找不到 <a> 或 <img> 標籤。")
            return None # 讓 Action 失敗

        # 1. 安全地取得 target_url
        href = link_tag.get('href')
        if not href:
             print("  [爬蟲錯誤!] <a> 標籤沒有 'href'。")
             return None
        target_url = f"{base_url}{href}"

        # 2. 安全地取得 title (這就是你 Bug 的修復！)
        #    我們用 .get('title', ...)
        #    如果 'title' 屬性不存在，它會用 formatted_code 當作「備案」標題
        title = img_tag.get('title', f"影片: {formatted_code}") 

        # 3. 安全地取得 external_image_url
        external_image_url = img_tag.get('src')
        if not external_image_url:
            print("  [爬蟲警告!] <img> 標籤沒有 'src'，使用預設圖片。")
            external_image_url = "https://via.placeholder.com/200x250.png?text=Image+Missing"
        
        # === 修正完畢 ===
        
        tags = ["video"] 
        
        # 8. 下載圖片邏輯 (跟漫畫一樣)
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        image_ext = Path(urlparse(external_image_url).path).suffix
        if not image_ext or image_ext == ".gif": # 我們不抓 gif
            image_ext = ".jpg" 

        our_new_filename = f"video_{formatted_code}{image_ext}"
        internal_image_path = images_dir / our_new_filename
        
        # 如果 external_image_url 只是預設圖，我們就「不要」下載
        if "placeholder.com" in external_image_url:
             print(f"  [爬蟲警告!] 圖片網址是預設圖，跳過下載。")
             internal_image_path = external_image_url
        else:
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
