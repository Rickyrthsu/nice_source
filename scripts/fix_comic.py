import json
import os
import time
import random
import io
from pathlib import Path
import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image

# --- 設定 ---
JSON_FILE = 'data.json'
IMAGES_DIR = Path('images')
DEFAULT_ICON = 'scripts/icon.jpg'

def download_cover_image(code):
    """
    核心下載邏輯 (從 scrape_comic.py 移植並簡化)
    回傳: 成功時回傳 'images/xxxx.jpg'，失敗回傳 None
    """
    scraper = cloudscraper.create_scraper()
    target_url = f"https://nhentai.net/g/{code}/"
    
    print(f"    └── 正在連線: {target_url}")

    try:
        response = scraper.get(target_url)
        if response.status_code != 200:
            print(f"    [X] 連線失敗 (Status: {response.status_code})")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        cover_div = soup.find('div', id='cover')
        
        if not cover_div:
            print("    [X] 找不到封面元素")
            return None

        img_tag = cover_div.find('img')
        image_url = img_tag.get('data-src') or img_tag.get('src')

        if not image_url:
            print("    [X] 找不到圖片網址")
            return None

        # 處理相對協定
        if image_url.startswith('//'):
            image_url = 'https:' + image_url

        # 下載圖片
        print(f"    └── 下載圖片串流: {image_url} ...")
        img_response = scraper.get(image_url)
        
        # 轉檔處理
        image_stream = io.BytesIO(img_response.content)
        img = Image.open(image_stream)

        # 確保 images 資料夾存在
        IMAGES_DIR.mkdir(exist_ok=True)

        # 轉 RGB 並存檔
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        filename = f"{code}.jpg"
        save_path = IMAGES_DIR / filename
        
        img.save(save_path, 'JPEG', quality=95, optimize=True)
        print(f"    [V] 成功儲存: {save_path}")
        
        # 回傳給 JSON 使用的路徑 (使用正斜線以相容各系統)
        return str(save_path).replace(os.sep, '/')

    except Exception as e:
        print(f"    [!] 發生例外錯誤: {e}")
        return None

def main():
    print("=== 開始批次修復資料庫圖片 ===")
    
    if not os.path.exists(JSON_FILE):
        print(f"找不到 {JSON_FILE}，請確認位置。")
        return

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_count = 0
    
    # 遍歷資料
    for index, item in enumerate(data):
        # 檢查條件：類別是 comic 且 圖片是用預設圖的
        if item.get('category') == 'comic' and item.get('imageUrl') == DEFAULT_ICON:
            code = item.get('code')
            title = item.get('title', 'Unknown')
            
            print(f"\n[{index+1}/{len(data)}] 發現缺圖: {title} (Code: {code})")
            
            # 執行下載
            new_image_path = download_cover_image(code)
            
            if new_image_path:
                # 更新資料
                item['imageUrl'] = new_image_path
                updated_count += 1
                
                # 為了安全，每修復一個就存檔一次 (避免程式中斷導致做白工)
                with open(JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 隨機延遲 2~5 秒，模擬人類行為，非常重要！
            delay = random.uniform(2, 5)
            print(f"    Waiting {delay:.2f}s...")
            time.sleep(delay)

    print(f"\n=== 修復完成！共更新了 {updated_count} 筆資料 ===")

if __name__ == "__main__":
    main()