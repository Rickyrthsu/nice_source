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
    
    # 找到所有「標籤」 (例如 "女優:", "類型:")
    all_spans = soup.find_all('span', class_='text-secondary')
    
    for span in all_spans:
        label = span.text.strip().replace(':', '') # 取得 "女優", "類型"
        if not label:
            continue
            
        # 「值」就在「標籤」的「下一個元素」
        value_element = span.find_next_sibling()
        
        if value_element:
            # 找出所有的 <a> 標籤 (例如 女優, 類型)
            links = value_element.find_all('a')
            if links:
                # 把所有 <a> 標籤的文字抓出來
                values = [a.text.strip() for a in links if a.text]
                details[label] = values
            else:
                # 如果沒有 <a> 標籤 (例如 發行日期, 標題)
                value = value_element.text.strip()
                if value:
                    details[label] = value
                    
    # 為了方便 app.js 處理，我們統一 key 的名稱
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
    
    # 1. 格式化
    formatted_code = code.replace(" ", "-").upper()
    encoded_code = quote(formatted_code)
    
    # 2. 組合搜尋網址
    base_url = "https://missav.ws"
    search_url = f"{base_url}/search/{encoded_code}"
    print(f"  [爬蟲第 1 步] 正在用 Cloudscraper 抓取「搜尋頁」: {search_url}")

    # 3. 建立爬蟲
    scraper = cloudscraper.create_scraper()
    
    try:
        # 4. 抓取「搜尋頁」
        response = scraper.get(search_url)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 5. 尋找【第一筆】結果
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
                "details": {} # 給一個空的 details
            }

        print("  [爬蟲第 2 步] 成功在 HTML 中找到第一筆結果。")
        
        # 6. 【【【 已修正：用「安全」的方式解析 】】】
        link_tag = first_result.find('a')
        img_tag = first_result.find('img')

        if not link_tag or not img_tag:
            print("  [爬蟲錯誤!] 找到 thumbnail，但找不到 <a> 或 <img> 標籤。")
            return None

        # 1. (已修正) 取得 target_url
        href = link_tag.get('href')
        target_url = href if href.startswith('http') else f"{base_url}{href}"

        # 2. (已修正) 取得圖片 (優先抓 data-src)
        external_image_url = img_tag.get('data-src', img_tag.get('src'))
        if not external_image_url:
            external_image_url = "https://via.placeholder.com/200x250.png?text=Image+Missing"

        # 3. (已修正) 取得 title
        title = img_tag.get('title', f"影片: {formatted_code}") 
        
        # 7. 【【【 全新第 3 步：爬取「詳細頁面」】】】
        print(f"  [爬蟲第 3 步] 正在爬取影片詳細頁: {target_url}")
        details = {}
        tags = ["video"]
        try:
            detail_response = scraper.get(target_url)
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            # 呼叫我們的新函式
            details = parse_details_page(detail_soup)
            
            # 【【【 你的要求：把「類型」和「標籤」合併 】】】
            tags.extend(details.get('genres', []))
            tags.extend(details.get('labels', []))