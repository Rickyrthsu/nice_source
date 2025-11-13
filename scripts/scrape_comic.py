import os
import json
import requests
import sys
import shutil 
from pathlib import Path 

# --- 輔助函式：爬取 nhentai ---
def scrape_comic(code):
    print(f"  [函式: scrape_comic] 開始爬取 {code}...")
    print(f"  [爬蟲第 1 步] 正在抓取「API」: https://nhentai.net/api/gallery/{code}")

    try:
        api_url = f"https://nhentai.net/api/gallery/{code}"
        response = requests.get(api_url)
        response.raise_for_status() 
        data = response.json()
        
        media_id = data["media_id"]
        title = data["title"].get("pretty", data["title"].get("english", "N/A")) 
        tags = [tag["name"] for tag in data["tags"]]
        
        thumb_info = data["images"]["thumbnail"]
        thumb_type = 'jpg' if thumb_info["t"] == 'j' else 'png'
        
        external_image_url = f"https://t.nhentai.net/galleries/{media_id}/thumb.{thumb_type}"
        target_url = f"https://nhentai.net/g/{code}/"
        
        print(f"  [爬蟲第 2 步] API 抓取成功。找到「縮圖」網址: {external_image_url}")

        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True) 
        
        our_new_filename = f"{code}.{thumb_type}"
        internal_image_path = images_dir / our_new_filename
        
        final_image_url_to_save = ""
        
        try:
            print(f"  [爬蟲第 3 步] 正在從 {external_image_url} 下載圖片...")
            image_response = requests.get(external_image_url, stream=True)
            image_response.raise_for_status() 
            
            with open(internal_image_path, 'wb') as f:
                image_response.raw.decode_content = True
                shutil.copyfileobj(image_response.raw, f)
            print(f"  [爬蟲第 4 步] 圖片已成功儲存到: {internal_image_path}")
            
            final_image_url_to_save = str(internal_image_path)
            
        except Exception as img_e:
            print(f"  [爬蟲警告!] 圖片「下載失敗」: {img_e}")
            
            # ===【【【 你的「小微調」在這裡！】】】===
            # 舊的: "icon.png" (錯誤)
            # 新的: "images/icon.png" (正確，假設你把 icon.png 放在 images/ 裡)
            final_image_url_to_save = "images/icon.png"
            # ===【【【 微調完畢 】】】===

        result = {
            "title": title,
            "code": code,
            "imageUrl": final_image_url_to_save, 
            "targetUrl": target_url,       
            "tags": tags
        }
        return result

    except Exception as e:
        print(f"  [函式: scrape_comic] 爬取漫畫 {code} 失敗 (API 錯誤): {e}")
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
    new_entry = scrape_comic(cvalue)
    
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
