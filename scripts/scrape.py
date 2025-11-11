import os
import json
import requests
import sys
from bs4 import BeautifulSoup # 用於爬取動漫連結

# --- 輔助函式：爬取 nhentai ---
def scrape_comic(code):
    try:
        api_url = f"https://nhentai.net/api/gallery/{code}"
        response = requests.get(api_url)
        response.raise_for_status() # 如果失敗 (404, 500) 會拋出錯誤
        data = response.json()
        
        media_id = data["media_id"]
        title = data["title"]["pretty"]
        tags = [tag["name"] for tag in data["tags"]]
        first_page = data["images"]["pages"][0]
        page_type = 'jpg' if firstPage["t"] == 'j' else 'png'
        
        return {
            "title": title,
            "code": code,
            "imageUrl": f"https://i.nhentai.net/galleries/{media_id}/1.{page_type}",
            "targetUrl": f"https://nhentai.net/g/{code}",
            "tags": tags
        }
    except Exception as e:
        print(f"爬取漫畫 {code} 失敗: {e}")
        return None

# --- 輔助函式：爬取影片 (目前是範本) ---
def scrape_video(code):
    # 【未來】你可以在這裡實作影片的爬蟲邏輯
    # 目前先回傳一個假資料
    print(f"影片 {code} 的爬蟲尚未實作，使用範本資料")
    return {
        "title": f"影片範本: {code}",
        "code": code,
        "imageUrl": "https://via.placeholder.com/200x250",
        "targetUrl": "#",
        "tags": ["video", "placeholder"]
    }

# --- 輔助函式：爬取動漫 (通用連結) ---
def scrape_anime(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 抓取 Open Graph (og) 標籤，這是最標準的
        title = soup.find('meta', property='og:title')
        image = soup.find('meta', property='og:image')
        
        return {
            "title": title['content'] if title else "找不到標題",
            "imageUrl": image['content'] if image else "https://via.placeholder.com/200x250",
            "targetUrl": url,
            "tags": ["anime"] # 自動上標籤
        }
    except Exception as e:
        print(f"爬取動漫 {url} 失敗: {e}")
        return None

# --- 主程式 ---
def main():
    # 1. 從 Action 的表單獲取輸入值
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到類別或輸入值")
        sys.exit(1) # 結束腳本
        
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
        sys.exit(1)
        
    # 3. 加上 category 欄位
    new_entry['category'] = category_map.get(ctype, 'unknown')

    # 4. 讀取舊的 data.json
    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
    # 5. 將新資料插入到最前面
    data.insert(0, new_entry)
    
    # 6. 寫回 data.json
    with open(data_file, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 確保中文不會變亂碼
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"成功新增: {new_entry.get('title')}")

if __name__ == "__main__":
    main()