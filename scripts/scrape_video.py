import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper 
from urllib.parse import urlparse, parse_qs, quote 

# --- 輔助函式：解析 MissAV 詳細頁面 ---
def parse_details_page(soup):
    details = {}
    all_tags = [] 
    container = soup.find('div', class_='space-y-2')
    if not container:
        return {}, []

    rows = container.find_all('div', class_='text-secondary')
    for row in rows:
        label_tag = row.find('span')
        if not label_tag: continue
        label = label_tag.text.strip().replace(':', '')
        if not label: continue
            
        if label in ['番號', '標題']:
            value_tag = row.find('span', class_='font-medium')
            if value_tag: details[label] = value_tag.text.strip()
        elif label == '發行日期':
            value_tag = row.find('time')
            if value_tag: details[label] = value_tag.text.strip()
        else:
            links = row.find_all('a')
            if links:
                values = [a.text.strip() for a in links if a.text]
                if label in ['類型', '標籤']:
                    all_tags.extend(values)
                else:
                    details[label] = values
    
    final_details = {
        'release_date': details.get('發行日期'),
        'actress': details.get('女優', []),
        'male_actor': details.get('男優', []),
        'series': details.get('系列'),
        'studio': details.get('發行商'),
        'director': details.get('導演', [])
    }
    return final_details, all_tags

# --- Pornhub 爬蟲函式 ---
def scrape_pornhub(url):
    print(f"  [函式: scrape_pornhub] 開始爬取 {url}...")
    scraper = cloudscraper.create_scraper()

    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        viewkey = qs.get('viewkey', [None])[0]
        
        if not viewkey:
            viewkey = url.split('viewkey=')[-1] if 'viewkey=' in url else url.split('/')[-1]

        response = scraper.get(url)
        if response.status_code != 200:
            print(f"  [錯誤] 連線失敗 Status: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = ""
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title.get('content', '')
        else:
            h1 = soup.find('h1', class_='titleText')
            if h1: title = h1.text.strip()

        image_url = ""
        meta_image = soup.find('meta', property='og:image')
        if meta_image:
            image_url = meta_image.get('content', '')
            
        tags = ["porn", "pornhub"]
        tags_wrapper = soup.find('div', class_='tagsWrapper')
        if tags_wrapper:
            tag_links = tags_wrapper.find_all('a')
            for tag in tag_links:
                tag_text = tag.text.strip()
                if tag_text and "Pornhub" not in tag_text and "Premium" not in tag_text:
                    tags.append(tag_text)

        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        filename = f"porn_{viewkey}.jpg"
        save_path = images_dir / filename
        
        final_image_path = "https://via.placeholder.com/200x250.png?text=No+Image"
        
        if image_url:
            print(f"  [Pornhub] 下載封面: {image_url}")
            try:
                img_response = scraper.get(image_url, stream=True)
                if img_response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        img_response.raw.decode_content = True
                        shutil.copyfileobj(img_response.raw, f)
                    final_image_path = str(save_path).replace(os.sep, '/')
                    print(f"  [Pornhub] 圖片儲存成功: {final_image_path}")
            except Exception as img_e:
                print(f"  [Pornhub] 圖片下載失敗: {img_e}")

        return {
            "title": title,
            "code": f"PH-{viewkey}", 
            "imageUrl": final_image_path,
            "targetUrl": url,
            "tags": tags,
            "details": {
                "studio": ["Pornhub"]
            },
            "category": "porn"
        }

    except Exception as e:
        print(f"  [Pornhub] 發生例外錯誤: {e}")
        return None

# --- 輔助函式：爬取 MissAV ---
def scrape_missav(code):
    print(f"  [函式: scrape_missav] 開始爬取 {code}...")
    scraper = cloudscraper.create_scraper()
    
    if code.startswith('http'):
         return {
            "title": f"類別錯誤: {code}",
            "code": "Error",
            "imageUrl": "https://via.placeholder.com/200x250.png?text=Use+Code", 
            "targetUrl": code, 
            "tags": ["video", "error"],
            "details": {},
            "category": "video"
         }

    formatted_code = code.replace(" ", "-").upper()
    encoded_code = quote(formatted_code)
    base_url = "https://missav.ws"
    search_url = f"{base_url}/search/{encoded_code}"

    try:
        response = scraper.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            return {
                "title": f"Google 搜尋: {formatted_code}",
                "code": formatted_code,
                "imageUrl": "https://via.placeholder.com/200x250.png?text=Not+Found", 
                "targetUrl": f"https://www.google.com/search?q=missav+{encoded_code}", 
                "tags": ["video", "not-found"],
                "details": {},
                "category": "video"
            }

        link_tag = first_result.find('a')
        img_tag = first_result.find('img')
        if not link_tag or not img_tag: return None

        href = link_tag.get('href')
        target_url = href if href.startswith('http') else f"{base_url}{href}"
        external_image_url = img_tag.get('data-src', img_tag.get('src'))
        title = img_tag.get('title', f"影片: {formatted_code}") 
        
        details = {}
        tags = ["video"]
        try:
            detail_response = scraper.get(target_url)
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            details, new_tags = parse_details_page(detail_soup)
            tags.extend(new_tags)
            detail_title = detail_soup.find('h1', class_='text-nord4')
            if detail_title: title = detail_title.text.strip()
        except: pass

        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        image_ext = ".jpg"
        internal_image_path = images_dir / f"video_{formatted_code}{image_ext}"
        
        try:
            image_response = requests.get(external_image_url, stream=True)
            with open(internal_image_path, 'wb') as f:
                image_response.raw.decode_content = True
                shutil.copyfileobj(image_response.raw, f)
            final_img_path = str(internal_image_path).replace(os.sep, '/')
        except:
            final_img_path = "https://via.placeholder.com/200x250.png?text=Error"

        return {
            "title": title,
            "code": formatted_code,
            "imageUrl": final_img_path,
            "targetUrl": target_url,
            "tags": tags, 
            "details": details,
            "category": "video"
        }

    except Exception as e:
        print(f"  [MissAV] 發生錯誤: {e}")
        return None

# --- 主程式 ---
def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 值={cvalue}")

    new_entry = None
    
    # ===【【【 關鍵修正：加入 Porn 類別對應 】】】===
    category_map = { 
        '漫畫': 'comic', 
        '影片': 'video', 
        '動漫': 'anime', 
        'Porn': 'porn'  # <--- 就是少了這個！
    }
    
    if ctype == 'Porn':
        new_entry = scrape_pornhub(cvalue)
    elif ctype == '影片':
        new_entry = scrape_missav(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) 
        
    # 確保 category 正確 (如果爬蟲函式有回傳 category 就不會被 unknown 覆蓋)
    if 'category' not in new_entry:
        new_entry['category'] = category_map.get(ctype, 'unknown')
    else:
        # 雙重保險：如果爬蟲有回傳，但我們想強制統一，也可以用 map 覆蓋
        # 但既然爬蟲已經寫好 category='porn'，這裡我們就保留原值，或者用 map 確保一致
        new_entry['category'] = category_map.get(ctype, new_entry['category'])

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = []
    
    data.insert(0, new_entry)
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()