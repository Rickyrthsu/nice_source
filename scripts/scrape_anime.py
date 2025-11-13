import os
import json
import requests
import sys
import shutil 
from pathlib import Path 
from bs4 import BeautifulSoup
import cloudscraper 
from urllib.parse import urlparse, parse_qs

# --- 輔助函式：爬取動漫 ---
def scrape_anime(url):
    print(f"  [函式: scrape_anime] 開始爬取 {url}...")
    
    # 【【【 Bug 修正！】】】
    # 如果使用者「不小心」餵了 番號，我們只取 URL
    if not url.startswith('http'):
         print(f"  [爬蟲警告!] 你輸入的是 番號，但類別選「動漫」。")
         print(f"  [爬蟲警告!] 正在執行「Google Fallback」...")
         return {
            "title": f"類別錯誤: {url}",
            "code": "Error",
            "imageUrl": "https://via.placeholder.com/200x250.png?text=Wrong+Category", 
            "targetUrl": f"https://www.google.com/search?q={quote(url)}", 
            "tags": ["anime", "error"],
            "details": {} # 給一個空的 details
         }

    # 1. 建立「終極爬蟲」實例
    scraper = cloudscraper.create_scraper()
    
    try:
        # 2. 使用 scraper.get() 騙過 403
        response = scraper.get(url)
        response.raise_for_status() 
        
        # 3. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. 抓取標題和「外部」圖片網址 (不變)
        title_tag = soup.find('meta', property='og:title')
        image_tag = soup.find('meta', property='og:image')
        
        title = title_tag['content'] if title_tag else "找不到標題"
        external_image_url = image_tag['content'] if image_tag else "https://via.placeholder.com/200x250.png?text=Image+Failed"
        
        # 5. 【【【 抓取標籤 (不變) 】】】
        print("  [爬蟲第 2.5 步] 正在尋找 <meta name='keywords'>...")
        tags = ["anime"] 
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        
        if keywords_tag and keywords_tag.get('content'):
            keywords_content = keywords_tag.get('content')
            print(f"  [爬蟲第 2.6 步] 成功找到關鍵字: {keywords_content[:50]}...")
            tags = [tag.strip() for tag in keywords_content.split(',')]
        else:
            print("  [爬蟲警告!] 找不到 <meta name='keywords'> 標籤，使用預設 'anime' 標籤。")

        
        # 6. 【【【 下載圖片邏輯 (已修正 Bug B) 】】】
        images_dir = Path('images')
        images_dir.mkdir(exist_ok=True)
        
        # === 【【【 Bug B 修正！】】】 ===
        # 舊的: video_id = parse_qs(parsed_url.query).get('v', [None])[0] (太脆弱)
        
        # 新的 (更強健):
        parsed_url = urlparse(url)
        # 1. 試著抓 ?v=
        video_id_list = parse_qs(parsed_url.query).get('v') 
        
        if video_id_list: # 如果 video