import os
import json
import sys
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def get_anime_code(url):
    """從網址中萃取出獨一無二的代碼 (例如 v=103525 取 103525)"""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    
    if 'v' in qs:
        return qs['v'][0]
        
    # 如果沒有 ?v=，就取網址的最後一段路徑
    path_parts = [p for p in parsed.path.split('/') if p]
    if path_parts:
        return path_parts[-1]
        
    return "unknown"

def main():
    cvalue = os.environ.get('COLLECTION_VALUE')
    ctype = os.environ.get('COLLECTION_TYPE', '動漫')
    
    if not cvalue:
        print("錯誤：找不到輸入網址 (COLLECTION_VALUE)")
        sys.exit(1)

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 網址={cvalue}")

    # 使用 cloudscraper 保持與其他腳本一致
    scraper = cloudscraper.create_scraper()
    
    # 1. 爬取標題
    try:
        response = scraper.get(cvalue)
        if response.status_code != 200:
            print(f"❌ 連線失敗，狀態碼: {response.status_code}")
            title = "抓取失敗_請手動修改標題"
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = ""
            # 優先找 og:title
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')
            
            # 找不到就找 <title> 標籤
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.strip()
            
            if not title:
                title = "未知的動漫標題"
                
    except Exception as e:
        print(f"❌ 發生例外錯誤: {e}")
        title = "抓取錯誤_請手動修改標題"

    # 2. 準備 JSON 資料與圖片檔名
    code = get_anime_code(cvalue)
    image_filename = f"anime_{code}.jpg"
    image_path = f"images/{image_filename}" # 寫入 JSON 的路徑

    new_entry = {
        "title": title,
        "code": code,
        "imageUrl": image_path,
        "targetUrl": cvalue,
        "tags": ["anime"],
        "details": {},
        "category": "anime"
    }

    # 3. 讀取並寫入 data.json
    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
    # 插入到最前面
    data.insert(0, new_entry)
    
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ 成功將【{title}】寫入 data.json！")
        
        # 4. 明確提示使用者需放入的圖片名稱
        print(f"\n==================================================")
        print(f"📢 【請注意：需要手動上傳圖片】")
        print(f"請準備一張此動漫的封面圖，將其重新命名為：")
        print(f"👉 {image_filename}")
        print(f"並放入專案的 images/ 資料夾中，網頁才能正常顯示。")
        print(f"==================================================\n")
        
    except Exception as e:
        print(f"❌ 寫入 data.json 失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()