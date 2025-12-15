#!/usr/bin/env python3
"""
画像スクレイピングのテストスクリプト
"""
from services.scraper import ImageScraper

# テストURL
test_url = "https://lp.wonder-ma.com/7206/Truck-Olive"

print(f"🔍 Testing image extraction from: {test_url}\n")

scraper = ImageScraper(test_url)
result = scraper.extract_images()

print(f"📊 Results:")
print(f"  ✅ Logo URL: {result['logo_url']}")
print(f"  👤 Character URL: {result['character_url']}")

if result['logo_url']:
    print(f"\n✅ Logo image found!")
else:
    print(f"\n❌ Logo image NOT found")

if result['character_url']:
    print(f"✅ Character image found!")
else:
    print(f"❌ Character image NOT found")
    print(f"\n💡 Checking CSS selector...")

    # CSSセレクタを確認
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(test_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 現在のセレクタで検索
    selector = '.wonder-cv .wonder-cv-wrapper .wonder-cv-back-person-img'
    element = soup.select_one(selector)
    print(f"  Current selector: {selector}")
    print(f"  Found element: {element is not None}")

    if element:
        print(f"  Element tag: {element.name}")
        print(f"  Element attributes: {element.attrs}")

    # 代替セレクタを試す
    alternative_selectors = [
        '.wonder-cv-back-person-img',
        'img.wonder-cv-back-person-img',
        '.wonder-cv img',
        '[class*="person"]',
        '[class*="character"]',
        '[class*="cv"]'
    ]

    print(f"\n🔍 Trying alternative selectors...")
    for alt_selector in alternative_selectors:
        elements = soup.select(alt_selector)
        if elements:
            print(f"  ✅ '{alt_selector}' found {len(elements)} element(s)")
            for i, elem in enumerate(elements[:3]):  # 最大3つまで表示
                if elem.name == 'img' and elem.get('src'):
                    print(f"     [{i}] <img src='{elem.get('src')}'>")
                else:
                    print(f"     [{i}] {elem.name} - {elem.get('class')}")
