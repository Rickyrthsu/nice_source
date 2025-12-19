import os
import json
import sys
import io
from pathlib import Path
import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image

# --- 核心函式：爬取 nhentai (HTML 解析版) ---
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code} (使用 CloudScraper)...")
    
    # 1. 建立 Scraper 與目標網址
    scraper = cloudscraper.create_scraper()
    target_url = f"https://nhentai.net/g/{code}/"
    print(f"  [爬蟲第 1 步] 分析網頁 HTML: {target_url}")

    try:
        response = scraper.get(target_url)
        
        # 如果被擋 (403/503) 或找不到 (404)，直接報錯
        if response.status_code != 200:
            print(f"  [錯誤] 連線失敗，狀態碼: {response.status_code}")
            return None

        # 2. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- (A) 抓取標題 ---
        # 嘗試尋找 <div id="info"> 裡面的 <h1 class="title">
        # 裡面通常會有 <span class="pretty">，如果沒有就抓整個 h1 文字
        title_tag = soup.select_one('#info h1.title')
        if title_tag:
            # 優先抓 pretty title (較短的名稱)，沒有的話抓全部
            pretty_span = title_tag.select_one('.pretty')
            title = pretty_span.get_text(strip=True) if pretty_span else title_tag.get_text(strip=True)
        else:
            title = f"Unknown Title ({code})"
        
        # --- (B) 抓取標籤 (Tags) ---
        # 尋找所有 class="tag" 裡面的 class="name"
        # 排除掉不需要的標籤類別 (如 pages, uploaded 等，視需求而定，這裡先全抓)
        tag_elements = soup.select('.tag .name')
        tags = [t.get_text(strip=True) for t in tag_elements if t]

        # --- (C) 抓取圖片並轉檔 (你的 n.py 邏輯) ---
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # 設定存檔路徑 (統一為 jpg)
        final_filename = f"{code}.jpg"
        internal_image_path = images_dir / final_filename
        final_image_url_to_save = ""

        try:
            cover_div = soup.find('div', id='cover')
            if cover_div:
                img_tag = cover_div.find('img')
                # 優先抓 data-src
                raw_img_url = img_tag.get('data-src') or img_tag.get('src')
                
                # 處理 // 開頭的相對路徑
                if raw_img_url and raw_img_url.startswith('//'):
                    raw_img_url = 'https:' + raw_img_url
                
                print(f"  [爬蟲第 2 步] 找到封面原始圖檔: {raw_img_url}")

                # 下載圖片
                img_response = scraper.get(raw_img_url)
                
                # 記憶體內讀取與轉檔 (Pillow)
                image_stream = io.BytesIO(img_response.content)
                img = Image.open(image_stream)

                # 處理透明度 (RGBA -> RGB)
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGBA')
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # 儲存為 JPG
                img.save(internal_image_path, 'JPEG', quality=95, optimize=True)
                print(f"  [爬蟲第 3 步] 轉檔並儲存成功: {internal_image_path}")
                
                final_image_url_to_save = str(internal_image_path).replace(os.sep, '/') # 確保路徑格式統一

            else:
                print("  [警告] 找不到封面元素 (HTML 結構可能變更)")
                raise Exception("Cover element not found")

        except Exception as img_e:
            print(f"  [圖片錯誤] 下載或轉檔失敗: {img_e}")
            # 保持你的備用圖片邏輯
            final_image_url_to_save = "scripts/icon.jpg"

        # 回傳結果 (符合 data.json 格式)
        result = {
            "title": title,
            "code": code,
            "imageUrl": final_image_url_to_save, 
            "targetUrl": target_url,       
            "tags": tags
        }
        return result

    except Exception as e:
        print(f"  [嚴重錯誤] 爬取漫畫 {code} 發生例外: {e}")
        return None

# --- 主程式 (維持不變，負責讀取環境變數與寫檔) ---
def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到類別或輸入值 (COLLECTION_TYPE or COLLECTION_VALUE)")
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 值={cvalue}")

    new_entry = None
    # 這裡只處理漫畫，其他類型由其他腳本處理 (雖然這個腳本只會在 type=漫畫 時被呼叫)
    if ctype == '漫畫':
        new_entry = scrape_comic(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) 
        
    new_entry['category'] = 'comic' # 強制寫入 comic 類別

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
    # 將新資料插入最前面
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