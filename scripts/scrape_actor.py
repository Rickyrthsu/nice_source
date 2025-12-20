import os
import json
import sys
import shutil
import re
from pathlib import Path
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import quote, urlparse

# --- MissAV 爬蟲邏輯 (維持搜尋模式) ---
def scrape_missav_actor(name, scraper):
    print(f"  [MissAV] 正在搜尋: {name} ...")
    
    search_url = f"https://missav.ws/search/{quote(name)}"
    try:
        response = scraper.get(search_url)
        if response.status_code != 200:
            print(f"  [MissAV] 搜尋失敗: Status {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        actor_link = None
        # 尋找 href 包含 /actresses/ 的連結
        candidates = soup.find_all('a', href=re.compile(r'/actresses/'))
        
        for link in candidates:
            href = link.get('href', '')
            # 排除排行榜等無關連結
            if 'ranking' in href or 'search' in href:
                continue
            actor_link = href
            print(f"  [MissAV] 找到候選連結: {actor_link}")
            break
        
        if not actor_link:
            print(f"  [MissAV] 搜尋結果中找不到女優專屬頁面")
            return None

        if not actor_link.startswith('http'):
            actor_link = f"https://missav.ws{actor_link}"
            
        print(f"  [MissAV] 進入個人頁面: {actor_link}")
        profile_response = scraper.get(actor_link)
        profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
        
        image_url = ""
        # 策略 A: 找 fourhoi.com 的圖 (通常是官方頭像)
        imgs = profile_soup.find_all('img')
        for img in imgs:
            src = img.get('data-src') or img.get('src') or ""
            if 'fourhoi.com' in src and 'actress' in src:
                image_url = src
                print(f"  [MissAV] 找到 Fourhoi 圖片: {image_url}")
                break
        
        # 策略 B: 找 rounded-full 樣式的圖
        if not image_url:
            avatar_img = profile_soup.find('img', class_=lambda x: x and 'rounded-full' in x)
            if avatar_img:
                image_url = avatar_img.get('data-src') or avatar_img.get('src')
                print(f"  [MissAV] 透過樣式找到圖片: {image_url}")

        if not image_url:
            print("  [MissAV] 找不到頭像圖片 URL，將使用預設圖")
            return { 
                "name": name, # 回傳搜尋的名字
                "targetUrl": actor_link, 
                "imageUrl": "scripts/icon.jpg",
                "source": "missav"
            }

        return { 
            "name": name,
            "targetUrl": actor_link, 
            "imageUrl": image_url,
            "source": "missav"
        }

    except Exception as e:
        print(f"  [MissAV] 發生錯誤: {e}")
        return None

# --- Pornhub 爬蟲邏輯 (改為直連模式) ---
def scrape_pornhub_by_url(url, scraper):
    print(f"  [Pornhub] 正在解析網址: {url} ...")
    
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"  [Pornhub] 連線失敗 (Status {response.status_code})")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 抓取名字 (Title)
        # 通常在 <meta property="og:title"> 或 <h1> 裡面
        # Pornhub 的 title 格式通常是 "Name - Porn Videos..." 或 "Name | Pornhub"
        
        extracted_name = ""
        og_title = soup.find('meta', property='og:title')
        if og_title:
            raw_title = og_title.get('content', '')
            # 清理標題，只留下人名
            # 例如: "Yui Peachpie Porn Videos | Pornhub" -> "Yui Peachpie"
            extracted_name = raw_title.split('|')[0].split('-')[0].strip()
        
        if not extracted_name:
            # 備案: 找 h1
            h1 = soup.find('h1')
            if h1: extracted_name = h1.get_text(strip=True)
            
        if not extracted_name:
            # 最後手段: 從網址抓
            print("  [Pornhub] 無法從頁面抓取名字，嘗試從網址分析...")
            path = urlparse(url).path
            extracted_name = path.split('/')[-1].replace('-', ' ').title()

        print(f"  [Pornhub] 偵測到名字: {extracted_name}")

        # 2. 抓取頭像 (Image)
        image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            img_tag = soup.find('img', id='getAvatar')
            if img_tag:
                image_url = img_tag.get('src')
                
        if not image_url:
            print("  [Pornhub] 找不到頭像圖片")
            return None

        print(f"  [Pornhub] 抓到頭像 URL: {image_url}")

        return {
            "name": extracted_name,
            "targetUrl": url,
            "imageUrl": image_url,
            "source": "pornhub"
        }

    except Exception as e:
        print(f"  [Pornhub] 發生例外錯誤: {e}")
        return None

# --- 主邏輯 (路由分發) ---
def scrape_actor(input_str):
    scraper = cloudscraper.create_scraper()
    result_data = None
    
    # 簡單的輸入清洗
    input_str = input_str.strip()
    
    # === 判斷邏輯 ===
    # 1. 如果輸入是 URL 且包含 pornhub -> 走 Pornhub 直連
    if "pornhub.com" in input_str and input_str.startswith("http"):
        result_data = scrape_pornhub_by_url(input_str, scraper)
        
    # 2. 其他情況 -> 視為人名，走 MissAV 搜尋
    else:
        # 如果使用者還是習慣打 "名字,missav"，我們幫他把後面去掉
        clean_name = input_str.split(',')[0].strip()
        result_data = scrape_missav_actor(clean_name, scraper)

    if not result_data:
        print("爬取失敗，無法取得資料。")
        return None
        
    # --- 下載圖片並儲存 ---
    name = result_data['name']
    source = result_data['source']
    
    heads_dir = Path('images/heads')
    heads_dir.mkdir(parents=True, exist_ok=True)
    
    # 清理檔名 (只留安全字元)
    safe_filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_filename: safe_filename = "unknown_actor"
    
    local_filename = f"{safe_filename}.jpg"
    save_path = heads_dir / local_filename
    
    final_image_path = "scripts/icon.jpg" # 預設值

    # 如果抓到的圖不是預設 icon，就下載
    if result_data['imageUrl'] != "scripts/icon.jpg":
        try:
            print(f"正在下載頭像: {result_data['imageUrl']}")
            img_response = scraper.get(result_data['imageUrl'], stream=True)
            img_response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                img_response.raw.decode_content = True
                shutil.copyfileobj(img_response.raw, f)
                
            print(f"頭像已儲存: {save_path}")
            final_image_path = str(save_path).replace(os.sep, '/')
            
        except Exception as e:
            print(f"圖片下載失敗: {e}")
            final_image_path = "scripts/icon.jpg"
    else:
        print("使用預設圖示 (未找到圖片)")

    # 回傳 JSON 結構 (保持相容性)
    return {
        "title": name,
        "code": source, # 用 source (missav/pornhub) 當作 code
        "imageUrl": final_image_path,
        "targetUrl": result_data['targetUrl'],
        "tags": ["actor", source],
        "details": {},
        "category": "actor"
    }

# --- 程式入口 ---
def main():
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not cvalue:
        print("錯誤：找不到輸入值 (COLLECTION_VALUE)")
        sys.exit(1)

    new_entry = scrape_actor(cvalue)
    
    if not new_entry:
        sys.exit(1)

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
    data.insert(0, new_entry)
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("✅ 角色資料新增成功！")

if __name__ == "__main__":
    main()