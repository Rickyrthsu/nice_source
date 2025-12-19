import os
import json
import sys
import shutil
import io
from pathlib import Path
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import quote, urljoin

# --- MissAV 爬蟲邏輯 ---
def scrape_missav_actor(name, scraper):
    print(f"  [MissAV] 正在搜尋: {name} ...")
    
    # 1. 搜尋頁面
    search_url = f"https://missav.ws/search/{quote(name)}"
    try:
        response = scraper.get(search_url)
        if response.status_code != 200:
            print(f"  [MissAV] 搜尋失敗: Status {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 尋找「女優」的連結
        # MissAV 的搜尋結果頁面，若有符合的女優，通常會有一個連結包含 '/actresses/'
        # 我們搜尋所有連結，找到第一個包含 '/actresses/' 且文字包含名字的
        
        actor_link = None
        
        # 策略 A: 找含有 class="text-secondary" 或在特定區塊的連結 (比較困難預測 DOM)
        # 策略 B: 暴力搜尋所有 href 包含 'actresses' 的連結
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            if '/actresses/' in link['href']:
                # 簡單過濾：確保不是 sidebar 的隨機推薦 (通常搜尋結果會在大區塊)
                # 這裡假設搜尋精準度高，直接取第一個匹配的
                actor_link = link['href']
                print(f"  [MissAV] 找到女優頁面連結: {actor_link}")
                break
        
        if not actor_link:
            print(f"  [MissAV] 搜尋結果中找不到女優專屬頁面 (可能只有影片結果)")
            # 備案：如果是影片，可能很難精準抓頭像，這裡先回傳 None 或做進階處理
            return None

        # 3. 進入女優個人頁面
        if not actor_link.startswith('http'):
            actor_link = f"https://missav.ws{actor_link}"
            
        profile_response = scraper.get(actor_link)
        profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
        
        # 4. 抓取大頭貼
        # 通常在 header 區域，或是 og:image
        # 嘗試 1: og:image (通常最穩)
        image_url = ""
        og_image = profile_soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            # 嘗試 2: 找 img 標籤 (這比較吃運氣，先試著找看起來像頭像的)
            # MissAV 女優頁面通常有一個圓形或方形的大圖
            imgs = profile_soup.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                if 'fourhoi.com' in src or 'actress' in src:
                    image_url = src
                    break
        
        if not image_url:
            print("  [MissAV] 找不到頭像圖片 URL")
            return None

        return {
            "targetUrl": actor_link,
            "imageUrl": image_url
        }

    except Exception as e:
        print(f"  [MissAV] 發生錯誤: {e}")
        return None

# --- Pornhub 爬蟲邏輯 ---
def scrape_pornhub_actor(name, scraper):
    # Pornhub 網址結構通常是: pornstar/name-separated-by-dashes
    formatted_name = name.lower().replace(' ', '-')
    target_url = f"https://cn.pornhub.com/pornstar/{formatted_name}"
    
    print(f"  [Pornhub] 正在嘗試進入個人頁面: {target_url}")
    
    try:
        response = scraper.get(target_url)
        # Pornhub 搜尋不到會轉址或 404
        if response.status_code != 200:
            print(f"  [Pornhub] 找不到該女優 (Status {response.status_code})，可能需要手動確認拼字。")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 抓取大頭貼
        # 嘗試 1: og:image
        image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            # 嘗試 2: id="getAvatar" (Pornhub 常見結構)
            img_tag = soup.find('img', id='getAvatar')
            if img_tag:
                image_url = img_tag.get('src')
        
        if not image_url:
            print("  [Pornhub] 找不到頭像圖片 URL")
            return None

        return {
            "targetUrl": target_url,
            "imageUrl": image_url
        }

    except Exception as e:
        print(f"  [Pornhub] 發生錯誤: {e}")
        return None

# --- 主邏輯 ---
def scrape_actor(input_str):
    # 解析輸入: "名字,來源"
    if ',' not in input_str:
        print("錯誤：輸入格式必須為 '名字,來源' (例如: 美園和花,missav)")
        return None
        
    name, source = input_str.split(',', 1)
    name = name.strip()
    source = source.strip().lower()
    
    print(f"開始處理角色: {name} (來源: {source})")
    
    scraper = cloudscraper.create_scraper()
    result_data = None
    
    # 根據來源分流
    if 'missav' in source:
        result_data = scrape_missav_actor(name, scraper)
    elif 'pornhub' in source:
        result_data = scrape_pornhub_actor(name, scraper)
    else:
        print(f"錯誤：不支援的來源 '{source}'。目前僅支援 missav, pornhub")
        return None
        
    if not result_data:
        print("爬取失敗，無法取得資料。")
        return None
        
    # --- 下載圖片並儲存 ---
    # 設定路徑: images/heads/名字.jpg
    heads_dir = Path('images/heads')
    heads_dir.mkdir(parents=True, exist_ok=True) # 確保 heads 資料夾存在
    
    # 清理檔名 (避免特殊符號)
    safe_filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_filename: safe_filename = "unknown_actor"
    
    local_filename = f"{safe_filename}.jpg"
    save_path = heads_dir / local_filename
    
    try:
        print(f"正在下載頭像: {result_data['imageUrl']}")
        img_response = scraper.get(result_data['imageUrl'], stream=True)
        img_response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            img_response.raw.decode_content = True
            shutil.copyfileobj(img_response.raw, f)
            
        print(f"頭像已儲存: {save_path}")
        
    except Exception as e:
        print(f"圖片下載失敗: {e}")
        # 如果下載失敗，還是建立資料，但圖片設為預設
        save_path = "scripts/icon.jpg" # 或其他預設圖

    # 回傳 JSON 結構
    return {
        "title": name,
        "code": source, # 這裡用 source 當 code 標記，或者你可以放 actress id
        "imageUrl": str(save_path).replace(os.sep, '/'),
        "targetUrl": result_data['targetUrl'],
        "tags": ["actor", source], # 標記為 actor
        "details": {},
        "category": "actor"
    }

# --- 程式入口 ---
def main():
    # 這裡直接模擬 scrape_comic 的 main 結構
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not cvalue:
        print("錯誤：找不到輸入值 (COLLECTION_VALUE)")
        sys.exit(1)

    new_entry = scrape_actor(cvalue)
    
    if not new_entry:
        sys.exit(1)

    # 寫入 data.json
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