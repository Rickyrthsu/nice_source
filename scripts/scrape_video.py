import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper 
from urllib.parse import urlparse, quote 

# --- 【【【 全新輔助函式：用來解析詳細頁面 】】】 ---
def parse_details_page(soup):
    """
    解析「詳細頁面」的資料 (女優, 類型...)
    """
    details = {}
    all_spans = soup.find_all('span', class_='text-secondary')
    
    for span in all_spans:
        label = span.text.strip().replace(':', '') # 取得 "女優", "類型"
        if not label:
            continue
            
        value_element = span.find_next_sibling()
        
        if value_element:
            links = value_element.find_all('a')
            if links:
                values = [a.text.strip() for a in links if a.text]
                details[label] = values
            else:
                value = value_element.text.strip()
                if value:
                    details[label] = value
                    
    final_details = {
        'release_date': details.get('發行日期'),
        'actress': details.get('女優', []),
        'male_actor': details.get('男優', []),
        'genres': details.get('類型', []),
        'series': details.get('系列'),
        'studio': details.get('發行商'),
        'director': details.get('導演', []),
        'labels': details.get('標籤', [])
    }
    return final_details
# --- 【【【 輔助函式結束 】】】 ---


# --- 輔助函式：爬取影片 (MissAV) ---
def scrape_video(code):
    print(f"  [函式: scrape_video] 開始爬取 {code}...")
    
    # 【【【 Bug 修正！】】】
    # 如果使用者「不小心」餵了 URL，我們只取番號
    if code.startswith('http'):
         print(f"  [爬蟲警告!] 你輸入的是 URL，但類別選「影片」。")
         print(f"  [爬蟲警告!] 正在執行「Google Fallback」...")
         return {
            "title": f"類別錯誤: {code}",
            "code": "Error",
            "imageUrl": "https://via.placeholder.com/200x250.png?text=Wrong+Category", 
            "targetUrl": f"https://www.google.com/search?q={quote(code)}", 
            "tags": ["video", "error"],
            "details": {}
         }
    
    formatted_code = code.replace(" ", "-").upper()
    encoded_code = quote(formatted_code)
    
    base_url = "https://missav.ws"
    search_url = f"{base_url}/search/{encoded_code}"
    print(f"  [爬蟲第 1 步] 正在用 Cloudscraper 抓取「搜尋頁」: {search_url}")

    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(search_url)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        first_result = soup.find('div', class_='thumbnail')
        
        if not first_result:
            # === 【【【 Google Fallback 邏輯 】】】 ===
            print(f"  [爬蟲警告!] 在 MissAV 上找不到番號 {formatted_code}。")
            print(f"  [爬蟲警告!] 正在執行你的「Google Fallback」計畫...")
            return {
                "title": f"在 Google 搜尋: {formatted_code}",
                "code": formatted_code,
                "imageUrl": "https://via.placeholder.com/200x250.png?text=Not+Found", 
                "targetUrl": f"https://www.google.com/search?q=missav+{encoded_code}", 
                "tags": ["video", "not-found"],
                "details": {} 
            }

        print("  [爬蟲第 2 步] 成功在 HTML 中找到第一筆結果。")
        
        link_tag = first_result.find('a')
        img_tag = first_result.find('img')

        if not link_tag or not img_tag:
            print("  [爬蟲錯誤!] 找到 thumbnail，但找不到 <a> 或 <img> 標籤。")
            return None

        href = link_tag.get('href')
        target_url = href if href.startswith('http') else f"{base_url}{href}"

        external_image_url = img_tag.get('data-src', img_tag.get('src'))
        if not external_image_url:
            external_image_url = "https://via.placeholder.com/200x250.png?text=Image+Missing"

        title = img_tag.get('title', f"影片: {formatted_code}") 
        
        # 7. 【【【 全新第 3 步：爬取「詳細頁面」】】】
        print(f"  [爬蟲第 3 步] 正在爬取影片詳細頁: {target_url}")
        details = {}
        tags = ["video"]
        
        # ===【【【 這就是「錯誤」的地方！】】】===
        try:
            detail_response = scraper.get(target_url)
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            details = parse_details_page(detail_soup)
            
            tags.extend(details.get('genres', []))
            tags.extend(details.get('labels', []))
            
            detail_title_tag = detail_soup.find('h1', class_='text-nord4')
            if detail_title_tag:
                title = detail_title_tag.text.strip()

        # ===【【【 我「忘記」加的 except 在這裡！】】】===
        except Exception as e:
            print(f"  [爬蟲警告!] 爬取「詳細頁」失敗: {e}。只使用基本資料。")
        # ===【【【 修正完畢 】】】===
            
        
        # 8. 下載圖片邏輯 (不變)
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        image_ext = Path(urlparse(external_image_url).path).suffix
        if not image_ext or image_ext == ".gif" or "data:image" in external_image_url:
            image_ext = ".jpg"
            internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        else:
            our_new_filename = f"video_{formatted_code}{image_ext}"
            internal_image_path = images_dir / our_new_filename
            
            try:
                print(f"  [爬蟲第 4 步] 正在從 {external_image_url} 下載圖片...")
                image_response = requests.get(external_image_url, stream=True)
                image_response.raise_for_status() 
                
                with open(internal_image_path, 'wb') as f:
                    image_response.raw.decode_content = True
                    shutil.copyfileobj(image_response.raw, f)
                print(f"  [爬蟲第 5 步] 圖片已成功儲存到: {internal_image_path}")
                internal_image_path = str(internal_image_path)
                
            except Exception as img_e:
                print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
                internal_image_path = "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        print(f"  [函式: scrape_video] 爬取 {formatted_code} 成功！")
        return {
            "title": title,
            "code": formatted_code,
            "imageUrl": internal_image_path,
            "targetUrl": target_url,
            "tags": tags,
            "details": details 
        }
    except Exception as e:
        print(f"  [函式: scrape_video] 爬取影片 {code} 失敗: {e}")
        return None

# --- 主程式 (所有腳本共用的，100% 不用動) ---
def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到類別或輸入值 (COLLECTION_TYPE or COLLECTION_VALUE)")
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    print(f"開始處理: 類別={ctype}, 值={cvalue}")

    new_entry = None
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime' }
    
    # 這是這個檔案「唯一」的任務
    new_entry = scrape_video(cvalue)
    
    if not new_entry:
        print("爬取失敗，結束任務")
        sys.exit(1) 
        
    new_entry['category'] = category_map.get(ctype, 'unknown')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
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