import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re
from urllib.parse import urljoin

class ImageScraper:
    """指定されたURLから特定のCSSセレクタで画像を抽出するクラス"""

    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def extract_images(self) -> Dict[str, Optional[str]]:
        """
        ページから画像URLを抽出
        Returns:
            {
                'logo_url': str or None,
                'character_url': str or None
            }
        """
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            logo_url = self._extract_logo(soup)
            character_url = self._extract_character(soup)

            return {
                'logo_url': logo_url,
                'character_url': character_url
            }
        except Exception as e:
            raise Exception(f"Failed to fetch page: {str(e)}")

    def _extract_logo(self, soup: BeautifulSoup) -> Optional[str]:
        """ヘッダーロゴ画像のURLを抽出"""
        selector = '.wonder-header .wonder-header-inner .wonder-header-logo-wrapper .wonder-header-main .wonder-header-logo img'
        img_element = soup.select_one(selector)

        if img_element and img_element.get('src'):
            return urljoin(self.url, img_element['src'])
        return None

    def _extract_character(self, soup: BeautifulSoup) -> Optional[str]:
        """キャラクター画像のURLを抽出"""
        selector = '.wonder-cv .wonder-cv-wrapper .wonder-cv-back-person-img'
        element = soup.select_one(selector)

        if not element:
            return None

        # 要素自体が img タグの場合（最優先）
        if element.name == 'img' and element.get('src'):
            return urljoin(self.url, element['src'])

        # background-image から URL を抽出
        style = element.get('style', '')
        match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
        if match:
            return urljoin(self.url, match.group(1))

        # または子要素の img タグを探す
        img_element = element.find('img')
        if img_element and img_element.get('src'):
            return urljoin(self.url, img_element['src'])

        return None

    def download_image(self, image_url: str) -> bytes:
        """画像URLから画像データをダウンロード"""
        try:
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Failed to download image from {image_url}: {str(e)}")
