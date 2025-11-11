import os
import json
import requests
import sys
import shutil 
from bs4 import BeautifulSoup

# --- 輔助函式：爬取 nhentai ---
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code}...")
    
    # ===【使用 API (最穩定的方式)】===
    print(f"  [爬蟲第 1 步] 正在抓取「API」: https://nhentai.net/api/gallery/{code}")

    try:
        # 1. 組合 API 網址並發送請求
        api_url = f"https://nhentai.net/api/gallery/{code}"
        response = requests.get(api_url)
        response.raise_for_status() # 確保請求成功 (不是 404 或 500)
        data = response.json()
        
        # 2. 從 API 的 JSON 中解析資料
        media_id = data["media_id"]
        title = data["title"].get("pretty", data["title"].get("english", "N/A")) 
        tags = [tag["name"] for tag in data["tags"]]
        first_page = data["images"]["pages"][0]
        
        # 3. 判斷副檔名 (j=jpg, p=png)
        page_type = 'jpg' if first_page["t"] == 'j' else 'png'
        
        # 4. 組合「圖片本人」的網址 (這才是圖片真正的家)
        image_url_we_found = f"https://i.nhentai.net/galleries/{media_id}/1.{page_type}"
        
        # 5. 組合你「想點進去」的網址
        target_url = f"https://nhentai.net/g/{code}/1/"
        
        print(f"  [爬蟲第 2 步] API 抓取成功。找到圖片真正網址: {image_url_we_found}")

        # === 6.【【【你的要求：強健的圖片下載】】】===
        # (這段程式碼不會下載到本地，因為 Action 是在雲端)
        # (我們只是「確認」圖片網址是有效的)
        try:
            print(f"  [爬蟲第 3 步] 正在「測試下載」圖片...")
            # 我們用 HEAD 請求，只抓標頭，不抓圖檔，這樣最快
            image_response = requests.head(image_url_we_found)
            image_response.raise_for_status() # 確保圖片網址是 200 (OK)
            print(f"  [爬蟲第 4 步] 圖片網址確認有效。")
            
        except Exception as img_e:
            # 【關鍵！】如果圖片下載失敗
            print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
            print(f"  [爬蟲警告!] 但 API 資料已抓到，程式將繼續執行。")
            # 我們把圖片網址改成一個「預設」的錯誤圖示
            image_url_we_found = "https://via.placeholder.com/200x250.png?text=Image+Failed+to+Load"
        # === 下載完畢 ===

        # 7. 組合我們要「儲存」的資料格式
        result = {
            "title": title,
            "code": code,
            "imageUrl": image_url_we_found, # 這是我們找到的真正網址 (或是錯誤圖示)
            "targetUrl": target_url,       # 這是你指定的網頁網址
            "tags": tags
        }
        return result

    except Exception as e:
        # 這會捕捉到 404 (Not Found) 或 API 伺服器掛了
        print(f"  [函式: scrape_comic] 爬取漫畫 {code} 失敗 (API 錯誤): {e}")
        return None

# --- 輔助函式：爬取影片 (目前是範本，不動) ---
def scrape_video(code):
    print(f"  [函式: scrape_video] 影片 {code} 的爬蟲尚未實作，使用範本資料")
    return {
        "title": f"影片範本: {code}",
        "code": code,
        "imageUrl": "https://via.placeholder.com/200x250",
        "targetUrl": "#",
        "tags": ["video", "placeholder"]
    }

# --- 輔助函式：爬取動漫 (通用連結，不動) ---
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
        
        # 加上「強健」邏輯
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

# --- 主程式 (改回「方案 C」的 GitHub Actions 模式) ---
def main():
    
    # ===【改回 GitHub Actions 模式】===
    # 1. 從「環境變數」獲取輸入值
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到類別或輸入值 (COLLECTION_TYPE or COLLECTION_VALUE)")
        sys.exit(1) # 結束程式

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 值={cvalue}")

    # 2. 根據類別執行對應的爬蟲
    new_entry = None
    category_map = {
        '漫畫': 'comic',
        '影片': 'video',
        '動漫': 'anime'
    }
    
    if ctype == '漫畫':
        new_entry = scrape_comic(cvalue)
    elif ctype == '影片':
        new_entry = scrape_video(cvalue)
    elif ctype == '動漫':
        new_entry = scrape_anime(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) # 讓 Action 顯示失敗
        
    # 3. 加上 category 欄位
    new_entry['category'] = category_map.get(ctype, 'unknown')

    # 4. 讀取 data.json
    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"警告：找不到 {data_file}，將建立一個新的。")
        data = []
    
    # 5. 將新資料插入到最前面
    data.insert(0, new_entry)
    
    # 6. 寫回 data.json
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"--- [GitHub Actions 執行完畢] ---")
        print(f"✅ 成功新增資料到 data.json！")
        
    except Exception as e:
        print(f"❌ 寫入 data.json 失敗: {e}")
        sys.exit(1)

# --- (這部分不變) ---
if __name__ == "__main__":
    main()