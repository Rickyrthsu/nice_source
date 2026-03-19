import json

def update_missav_urls(input_file_path, output_file_path):
    """
    讀取 JSON 檔案，將 targetUrl 中的 missav.ws 替換為 missav.ai，並輸出新檔案。
    """
    try:
        # 1. 讀取原始 JSON 資料
        with open(input_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        updated_count = 0
        
        # 2. 遍歷每一筆資料進行檢查與替換
        for item in data:
            # 檢查是否存在 targetUrl 欄位，且是否包含目標網域
            if 'targetUrl' in item and 'missav.ws' in item['targetUrl']:
                # 執行網址字串替換
                item['targetUrl'] = item['targetUrl'].replace('missav.ws', 'missav.ai')
                updated_count += 1
                
        # 3. 將更新後的資料寫入新的 JSON 檔案
        # ensure_ascii=False 確保繁體中文等非 ASCII 字元能正確顯示
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            
        print(f"資料處理完成！總共更新了 {updated_count} 筆網址。")
        print(f"更新後的檔案已儲存至：{output_file_path}")

    except FileNotFoundError:
        print(f"錯誤：找不到指定的輸入檔案 '{input_file_path}'，請確認檔案路徑是否正確。")
    except json.JSONDecodeError:
        print(f"錯誤：'{input_file_path}' 不是有效的 JSON 格式檔案。")
    except Exception as e:
        print(f"執行過程中發生未預期的錯誤：{e}")

# 設定輸入與輸出檔案名稱
input_filename = 'data.json'
output_filename = 'updated_data.json'

# 執行函式
if __name__ == '__main__':
    update_missav_urls(input_filename, output_filename)