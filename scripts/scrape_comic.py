import os
import json
import requests
import sys
import shutil 
from pathlib import Path 

# --- 輔助函式：爬取 nhentai ---
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code}...")
    # ... (你上傳的 程式碼... 100% 正確) ...
    print(f"  [爬蟲第 1 步] 正在抓取「API」: https://nhentai.net/api/gallery/{code}")

    try:
        api_url = f"https://nhentai.net/api/gallery/{code}"
        # ... (中略) ...
        result = {
            "title": title,
            "code": code,
            "imageUrl": str(internal_image_path), 
            "targetUrl": target_url,       
            "tags": tags
        }
        return result
    # ... (中略) ...
    except Exception as e:
        print(f"  [函式: scrape_comic] 爬取漫畫 {code} 失敗 (API 錯誤): {e}")
        return None

# --- 主程式 (所有腳本共用的) ---
def main():
    # ... (你上傳的 程式碼... 100% 正確) ...
    ctype = os.environ.get('COLLECTION_TYPE')
    # ... (中略) ...
    new_entry = scrape_comic(cvalue)
    # ... (中略) ...
    new_entry['category'] = category_map.get(ctype, 'unknown')
    # ... (中略) ...
    data.insert(0, new_entry)
    # ... (中略) ...
    json.dump(data, f, indent=2, ensure_ascii=False)
    # ... (中略) ...
if __name__ == "__main__":
    main()