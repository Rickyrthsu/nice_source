import os
import json
import sys
import shutil
import re
from pathlib import Path
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import quote, urljoin

# --- MissAV 爬蟲邏輯 (修正版) ---
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
        
        # 2. 尋找「搜尋結果」中的女優連結
        # 為了避免抓到 Header/Footer 的排行榜連結，我們嘗試縮小範圍
        # MissAV 的主要內容通常在 <div class="main-content"> 或類似結構，
        # 但為了通用，我們採取「過濾法」：
        #   (1) href 必須包含 '/actresses/'
        #   (2) href 不能包含 'ranking' 或 'new' (避免抓到排行榜)
        #   (3) 連結文字或 title 最好包含我們搜尋的名字 (Optional，視情況)
        
        actor_link = None
        
        # 找出頁面上所有包含 '/actresses/' 的連結
        # 並且排除掉明顯是導覽列的連結 (通常導覽列連結文字很短，或在特定清單中)
        candidates = soup.find_all('a', href=re.compile(r'/actresses/'))
        
        for link in candidates:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # 排除常見的導覽列連結 (這很重要！)
            if 'ranking' in href or 'search' in href:
                continue
                
            # 簡單判斷：通常搜尋結果的連結會包含名字，或者在 main grid 裡
            # 這裡我們取「第一個」看起來像結果的連結
            # MissAV 的個人頁面連結結構通常是: https://missav.ws/{server_node}/actresses/{name}
            # 我們檢查 href 是否以 /actresses/ 結尾 (有些是) 或包含名字
            
            # 為了更準確，我們檢查連結裡面是否包含搜尋的名字 (Url Encoded 之後的片段)
            # 或者如果是中文搜尋，MissAV 網址通常會是 UTF-8 編碼
            
            # 策略：直接抓取列表中的第一個「非導覽列」女優連結
            # 因為搜尋結果通常排在最前面 (在導覽列之後)
            actor_link = href
            print(f"  [MissAV] 找到候選連結: {actor_link}")
            break
        
        if not actor_link:
            print(f"  [MissAV] 搜尋結果中找不到女優專屬頁面 (可能只有影片結果)")
            return None

        # 3. 進入女優個人頁面
        if not actor_link.startswith('http'):
            # 處理相對路徑，確保域名正確
            actor_link = f"https://missav.ws{actor_link}"
            
        print(f"  [MissAV] 進入個人頁面: {actor_link}")
        profile_response = scraper.get(actor_link)
        profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
        
        # 4. 抓取大頭貼 (修正重點)
        # 使用者回報正確格式如: https://fourhoi.com/actress/1054998-t.jpg
        # 我們優先尋找 src 包含 'fourhoi.com' 且包含 'actress' 的圖片
        
        image_url = ""
        
        # 策略 A: 針對 fourhoi.com 進行特徵搜尋
        imgs = profile_soup.find_all('img')
        for img in imgs:
            src = img.get('data-src') or img.get('src') or ""
            if 'fourhoi.com' in src and 'actress' in src:
                image_url = src
                print(f"  [MissAV] 找到 Fourhoi 圖片: {image_url}")
                break
        
        # 策略 B: 如果上面沒找到，嘗試找 class 像是頭像的 (w-20, rounded-full 等)
        if not image_url:
            # MissAV 個人頁面大頭貼通常有 rounded-full 樣式
            avatar_img = profile_soup.find('img', class_=lambda x: x and 'rounded-full' in x)
            if avatar_img:
                image_url = avatar_img.get('data-src') or avatar_img.get('src')
                print(f"  [MissAV] 透過樣式找到圖片: {image_url}")

        if not image_url:
            print("  [MissAV] 找不到頭像圖片 URL")
            # 這裡不 return None，回傳連結讓使用者至少能連過去
            return {
                "targetUrl": actor_link,
                "imageUrl": "scripts/icon.jpg" # 暫時用預設圖
            }

        return {
            "targetUrl": actor_link,
            "imageUrl": image_url
        }

    except Exception as e:
        print(f"  [MissAV] 發生錯誤: {e}")
        return None

# --- Pornhub 爬蟲邏輯 (保持不變) ---
def scrape_pornhub_actor(name, scraper):
    formatted_name = name.lower().replace(' ', '-')
    target_url = f"https://cn.pornhub.com/pornstar/{formatted_name}"
    
    print(f"  [Pornhub] 正在嘗試進入個人頁面: {target_url}")
    
    try:
        response = scraper.get(target_url)
        if response.status_code != 200:
            print(f"  [Pornhub] 找不到該女優 (Status {response.status_code})")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            img_tag = soup.find('img', id='getAvatar')
            if img_tag:
                image_url = img_tag.get('src')
        
        if not image_url:
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
    
    if 'missav' in source:
        result_data = scrape_missav_actor(name, scraper)
    elif 'pornhub' in source:
        result_data = scrape_pornhub_actor(name, scraper)
    else:
        print(f"錯誤：不支援的來源 '{source}'")
        return None
        
    if not result_data:
        print("爬取失敗，無法取得資料。")
        return None
        
    # --- 下載圖片並儲存 ---
    heads_dir = Path('images/heads')
    heads_dir.mkdir(parents=True, exist_ok=True)
    
    # 清理檔名
    safe_filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_filename: safe_filename = "unknown_actor"
    
    local_filename = f"{safe_filename}.jpg"
    save_path = heads_dir / local_filename
    
    # 檢查是否為預設圖 (避免下載 icon.jpg)
    if result_data['imageUrl'] == "scripts/icon.jpg":
        final_image_path = "scripts/icon.jpg"
    else:
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

    # 回傳 JSON 結構
    return {
        "title": name,
        "code": source,
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