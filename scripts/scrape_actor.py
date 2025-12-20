import os
import json
import sys
import shutil
import re
from pathlib import Path
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import quote, urljoin

# --- MissAV 爬蟲邏輯 (保持不變) ---
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

# --- 【重點修改】Pornhub 爬蟲邏輯 (改用通用搜尋 + 暴力掃描) ---
def scrape_pornhub_actor(name, scraper):
    print(f"  [Pornhub] 正在搜尋: {name} ...")
    
    # 1. 改用最通用的「影片搜尋」接口
    # 因為 Pornhub 常常把 Model/Pornstar 的推薦放在影片搜尋結果的最上面或混合在裡面
    search_url = f"https://cn.pornhub.com/video/search?search={quote(name)}"
    print(f"  [Pornhub] 搜尋 URL: {search_url}")
    
    try:
        response = scraper.get(search_url)
        if response.status_code != 200:
            print(f"  [Pornhub] 搜尋請求失敗 (Status {response.status_code})")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 尋找 Profile 連結
        # 我們不依賴特定的 ID，而是直接掃描所有 <a> 標籤
        # 目標：找到 href="/model/xxx" 或 href="/pornstar/xxx"
        # 且必須是「主頁」 (結尾不能是 /videos, /photos 等)
        
        target_profile_url = None
        
        # Regex 解釋：
        # ^/(model|pornstar)/  -> 以 /model/ 或 /pornstar/ 開頭
        # [^/]+                -> 接著是名字 (不能包含斜線，確保只抓到主層級)
        # /?$                  -> 結尾可能是斜線也可能沒有，但後面不能再有其他路徑
        pattern = re.compile(r'^/(model|pornstar)/[^/]+/?$')
        
        # 抓取所有符合的連結
        candidates = soup.find_all('a', href=pattern)
        
        for link in candidates:
            href = link['href']
            
            # 排除掉一些明顯不對的 (雖然 regex 已經擋掉大部分)
            # 優先權：如果有包含搜尋關鍵字的連結，優先選用
            # 但通常第一個出現的都是最相關的 (Pornhub 的搜尋排序)
            
            print(f"  [Pornhub] 發現候選連結: {href}")
            
            # 組合成完整網址
            target_profile_url = f"https://cn.pornhub.com{href}"
            
            # 找到第一個就跳出 (通常是最佳結果)
            break
            
        if not target_profile_url:
            # 備案：有時候可能是 /users/ (針對一般用戶型 Model)
            # 如果上面沒找到，試試看 /users/
            user_pattern = re.compile(r'^/users/[^/]+/?$')
            user_candidates = soup.find_all('a', href=user_pattern)
            for link in user_candidates:
                # 排除系統連結 (如 login, signup 等)
                if any(x in link['href'] for x in ['login', 'signup', 'upload']): continue
                
                print(f"  [Pornhub] 發現 Users 候選連結: {link['href']}")
                target_profile_url = f"https://cn.pornhub.com{link['href']}"
                break

        if not target_profile_url:
            print(f"  [Pornhub] 搜尋結果中找不到任何 Model/Pornstar/User 的主頁連結: {name}")
            return None
            
        print(f"  [Pornhub] 鎖定個人頁面: {target_profile_url}")
        
        # 3. 進入個人頁面抓頭像 (這部分維持不變)
        profile_response = scraper.get(target_profile_url)
        profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
        
        image_url = ""
        # 嘗試 1: og:image
        og_image = profile_soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']
        else:
            # 嘗試 2: img id="getAvatar"
            img_tag = profile_soup.find('img', id='getAvatar')
            if img_tag:
                image_url = img_tag.get('src')
            else:
                # 嘗試 3: 針對 /users/ 頁面，頭像可能在不同結構
                # 找 class="user-avatar" 或類似
                avatar_div = profile_soup.find('div', id='avatar')
                if avatar_div:
                    img = avatar_div.find('img')
                    if img: image_url = img.get('src')

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
    
    safe_filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_filename: safe_filename = "unknown_actor"
    
    local_filename = f"{safe_filename}.jpg"
    save_path = heads_dir / local_filename
    
    final_image_path = "scripts/icon.jpg"

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