import os
import json
import sys
from pathlib import Path

def main():
    print("--- [GitHub Actions 刪除中] ---")
    
    # 1. 從「環境變數」獲取要刪除的番號
    code_to_delete = os.environ.get('DELETE_CODE')
    
    if not code_to_delete:
        print("錯誤：找不到要刪除的番號 (DELETE_CODE)")
        sys.exit(1) # 結束程式

    print(f"準備刪除番號: {code_to_delete}")
    
    data_file = 'data.json'
    data = []
    
    # 2. 讀取 data.json
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到 {data_file}。")
        sys.exit(1)
        
    if not data:
        print("data.json 是空的，沒有東西可以刪除。")
        return

    # 3. 找出要刪除的項目，並「同時」建立一個「新」的資料列表
    new_data = []
    item_found = False
    image_to_delete = None

    for item in data:
        # .get('code') 可以安全地處理沒有 'code' 欄位的項目 (例如動漫)
        if item.get('code') == code_to_delete:
            # 找到了！
            item_found = True
            print(f"找到了! 準備刪除: {item.get('title')}")
            
            # 順便記錄一下它對應的圖片路徑
            image_path = item.get('imageUrl')
            if image_path and image_path.startswith('images/'):
                image_to_delete = image_path
            
            # 【關鍵】我們「跳過 (skip)」它，不把它加回 new_data
            pass
        else:
            # 這不是我們要刪的，把它加回 new_data
            new_data.append(item)

    if not item_found:
        print(f"警告：在 data.json 中找不到番號 {code_to_delete}，任務結束。")
        sys.exit(0) # 正常結束，因為這不算「錯誤」

    # 4. 【新功能】刪除實體的圖片檔案 (如果有的話)
    if image_to_delete:
        try:
            image_path_obj = Path(image_to_delete)
            if image_path_obj.exists():
                os.remove(image_path_obj)
                print(f"成功刪除圖片檔案: {image_to_delete}")
            else:
                print(f"警告：找不到圖片檔案 {image_to_delete}，略過刪除。")
        except Exception as e:
            print(f"刪除圖片時發生錯誤: {e}")

    # 5. 把「乾淨」的 new_data 寫回 data.json
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        print(f"--- [GitHub Actions 刪除完畢] ---")
        print(f"✅ 成功從 data.json 刪除 {code_to_delete}！")
        
    except Exception as e:
        print(f"❌ 寫回 data.json 時失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()