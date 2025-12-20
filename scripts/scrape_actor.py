import os
import json
import sys
import shutil
import re
from pathlib import Path
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import quote, urljoin

# --- MissAV 爬蟲邏輯 (保持之前修正好的版本) ---
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
        candidates = soup.find_all('a', href=re.compile(r'/actresses/'))
        
        for link in candidates:
            href = link.get('href', '')
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
        imgs = profile_soup.find_all('img')
        for img in imgs:
            src = img.get('data-src') or img.get('src') or ""
            if 'fourhoi.com' in src and 'actress' in src:
                image_url = src
                print(f"  [MissAV] 找到 Fourhoi 圖片: {image_url}")
                break
        
        if not image_url:
            avatar_img = profile_soup.find('img', class_=lambda x: x and 'rounded-full' in x)
            if avatar_img:
                image_url = avatar_img.get('data-src') or avatar_img.get('src')
                print(f"  [MissAV] 透過樣式找到圖片: {image_url}")

        if not image_url:
            return { "targetUrl": actor_link, "imageUrl": "scripts/icon.jpg" }

        return { "targetUrl": actor_link, "imageUrl": image_url }

    except Exception as e:
        print(f"  [MissAV] 發生錯誤: {e}")
        return None

# --- 【重點修改】Pornhub 爬蟲邏輯 (改為搜尋模式) ---
def scrape_pornhub_actor(name, scraper):
    print(f"  [Pornhub] 正在搜尋: {name} ...")
    
    # 1. 使用「Pornstar 搜尋」接口 (比 video search 更準確找到人)
    # 網址範例: https://cn.pornhub.com/pornstars/search?search=yui+peachpie
    search_url = f"https://cn.pornhub.com/pornstars/search?search={quote(name)}"
    print(f"  [Pornhub] 搜尋 URL: {search_url}")
    
    try:
        response = scraper.get(search_url)
        if response.status_code != 200:
            print(f"  [Pornhub] 搜尋請求失敗 (Status {response.status_code})")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 解析搜尋結果列表
        # Pornhub 的演員搜尋結果通常包在 <ul id="pornstarsSearchResult"> 裡面
        result_container = soup.find('ul', id='pornstarsSearchResult')
        
        target_profile_url = None
        
        if result_container:
            # 抓第一筆結果 (li)
            first_item = result_container.find('li')
            if first_item:
                # 尋找裡面的連結 (通常標題或圖片都會包在 <a> 裡面)
                # 連結通常是 /pornstar/xxxx
                link_tag = first_item.find('a', href=re.compile(r'/pornstar/'))
                if link_tag:
                    href = link_tag['href']
                    target_profile_url = f"https://cn.pornhub.com{href}"
        
        if not target_profile_url:
            print(f"  [Pornhub] 搜尋結果為空，或是找不到符合的演員: {name}")
            return None
            
        print(f"  [Pornhub] 鎖定個人頁面: {target_profile_url}")
        
        # 3. 進入個人頁面抓頭像 (這部分維持不變，因為頁面結構一樣)
        profile_response = scraper.get(target_profile_url)
        profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
        
        image_url = ""
        # 優先抓 meta og:image (通常最清晰)
        og_image = profile_soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            # 備案：抓 img id="getAvatar"
            img_tag = profile_soup.find('img', id='getAvatar')
            if img_tag:
                image_url = img_tag.get('src')
        
        if not image_url:
            print("  [Pornhub] 在個人頁面找不到頭像")
            return None

        print(f"  [Pornhub] 抓到頭像 URL: {image_url}")

        return {
            "targetUrl": target_profile_url,
            "imageUrl": image_url
        }

    except Exception as e:
        print(f"  [Pornhub] 發生例外錯誤: {e}")
        return None

# --- 主邏輯 (路由) ---
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
    
    # 清理檔名 (只留安全字元)
    safe_filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_filename: safe_filename = "unknown_actor"
    
    local_filename = f"{safe_filename}.jpg"
    save_path = heads_dir / local_filename
    
    final_image_path = "scripts/icon.jpg" # 預設值

    # 如果抓到的圖是 icon.jpg (代表失敗) 就不下載
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