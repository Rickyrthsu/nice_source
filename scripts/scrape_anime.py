import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from urllib.parse import urlparse, parse_qs

def scrape_anime(cvalue):
    print(f"--- [手動模式啟動] ---")
    
    # 預期格式: 影片連結 , 標題 , 圖片連結
    try:
        if "," not in cvalue:
            print("❌ 錯誤：請使用『影片連結 , 標題 , 圖片連結』格式輸入！")
            return None
            
        parts = [p.strip() for p in cvalue.split(',')]
        if len(parts) < 3:
            print("❌ 錯誤：資料不足，請確保有兩個『,』分隔符號。")
            return None
        
        target_url = parts[0]
        title = parts[1]
        external_image_url = parts[2]
        
        print(f"📡 接收到手動資料：")
        print(f"   - 標題: {title}")
        print(f"   - 網址: {target_url}")
        print(f"   - 圖片: {external_image_url}")

        # 1. 處理圖片下載路徑
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # 嘗試從網址提取 v= ID 作為檔名，失敗就用標題
        parsed_url = urlparse(target_url)
        video_id_list = parse_qs(parsed_url.query).get('v') 
        video_id = video_id_list[0] if video_id_list else "manual_" + title[:10]
        
        # 強制存成 webp
        image_filename = f"anime_{video_id}.webp"
        internal_image_path = images_dir / image_filename
        
        # 2. 下載圖片 (帶上 Referer 避開簡單的圖片防盜連)
        print(f"💾 正在下載封面圖...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': 'https://hanime1.me/'
            }
            r = requests.get(external_image_url, headers=headers, stream=True, timeout=15)
            r.raise_for_status()
            
            with open(internal_image_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            print(f"✨ 圖片已成功儲存：{internal_image_path}")
            final_img_path = str(internal_image_path)
        except Exception as img_e:
            print(f"⚠️ 圖片下載失敗: {img_e}，回退使用原始網址。")
            final_img_path = external_image_url

        # 3. 回傳資料結構
        return {
            "title": title,
            "imageUrl": final_img_path, 
            "targetUrl": target_url,
            "tags": ["manual_add"], 
            "details": {}
        }

    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        return None

def main():
    ctype = os.environ.get('COLLECTION_TYPE')
    cvalue = os.environ.get('COLLECTION_VALUE')
    
    if not ctype or not cvalue:
        print("錯誤：找不到輸入值")
        sys.exit(1) 

    print(f"--- [GitHub Actions 執行中] ---")
    new_entry = scrape_anime(cvalue)
    
    if not new_entry:
        sys.exit(1) 
        
    category_map = { '漫畫': 'comic', '影片': 'video', '動漫': 'anime' }
    new_entry['category'] = category_map.get(ctype, 'unknown')

    data_file = 'data.json'
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    
    data.insert(0, new_entry)
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 成功新增資料到 data.json！")

if __name__ == "__main__":
    main()