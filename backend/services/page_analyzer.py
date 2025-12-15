"""
Gemini (Lambda経由) を使用してページを分析し、動画生成プロンプトを生成する
"""
import os
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from .gemini_client import GeminiClient


class PageAnalyzer:
    """Gemini (Lambda経由) を使用してページコンテンツを分析"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Args:
            secret_key: Lambda Secret Key（環境変数 LAMBDA_SECRET_KEY から取得も可能）
        """
        self.secret_key = secret_key or os.getenv('LAMBDA_SECRET_KEY')
        self.gemini_client = GeminiClient(secret_key)

    def analyze_page(self, url: str) -> Dict[str, str]:
        """
        ページを分析して商材情報とプロンプトを生成

        Args:
            url: 分析するページのURL

        Returns:
            {
                'product_name': str,  # 商材名
                'target_audience': str,  # ターゲット
                'main_benefit': str,  # 主なベネフィット
                'generated_prompt': str,  # 生成されたプロンプト
                'error': str (if failed)
            }
        """
        if not self.secret_key:
            return {
                'error': 'Lambda Secret Key not configured. Please set LAMBDA_SECRET_KEY in .env file'
            }

        try:
            # ページのHTMLを取得
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 本文テキストを抽出（スクリプトとスタイルを除外）
            for script in soup(["script", "style"]):
                script.decompose()

            text_content = soup.get_text()
            # 空白を整理
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = ' '.join(chunk for chunk in chunks if chunk)

            # テキストが長すぎる場合は制限
            if len(text_content) > 30000:
                text_content = text_content[:30000]

            # Gemini (Lambda経由) で分析
            prompt = f"""あなたは、指定されたWebページのコンテンツを分析し、P-MAX広告用の動画生成に必要な情報を抽出するAIアシスタントです。

以下の7つの要素を抽出・推測してください：

1. [商材/ブランド名]: h1タグ、titleタグ、またはロゴ周辺のテキストから最も適切な名称
2. [メインターゲット]: 「〜な方へ」「〜にお悩みでは？」などの記述からターゲット層を推測
3. [キャッチコピー]: ページのファーストビュー（FV）にある最も印象的で短いフレーズ
4. [ベネフィット1]: 商材が提供する最も重要な利点や特徴の1つ目
5. [ベネフィット2]: 商材が提供する2番目に重要な利点や特徴
6. [オファー]: 「無料トライアル」「限定割引」「キャンペーン中」などの行動喚起フレーズ。見つからない場合は「特に指定なし」
7. [CTAテキスト]: 「今すぐ購入」「資料請求」「無料で試す」など、ページ内の主要なボタンの文言

以下の形式で回答してください：
商材/ブランド名: [商材/ブランド名]
メインターゲット: [メインターゲット]
キャッチコピー: [キャッチコピー]
ベネフィット1: [ベネフィット1]
ベネフィット2: [ベネフィット2]
オファー: [オファー]
CTAテキスト: [CTAテキスト]

【ウェブページの内容】
{text_content}"""

            analysis_text = self._invoke_gemini(prompt)

            # 分析結果をパース
            product_info = self._parse_analysis(analysis_text)

            # プロンプトを生成
            generated_prompt = self._generate_video_prompt(product_info)

            return {
                'product_name': product_info.get('product_name', ''),
                'target_audience': product_info.get('target_audience', ''),
                'catchphrase': product_info.get('catchphrase', ''),
                'benefit1': product_info.get('benefit1', ''),
                'benefit2': product_info.get('benefit2', ''),
                'offer': product_info.get('offer', ''),
                'cta_text': product_info.get('cta_text', ''),
                'generated_prompt': generated_prompt,
                'raw_analysis': analysis_text,
                'page_url': url  # URLを追加して、画像抽出で使用できるようにする
            }

        except Exception as e:
            return {'error': f'Page analysis failed: {str(e)}'}

    def _parse_analysis(self, analysis_text: str) -> Dict[str, str]:
        """Geminiの分析結果をパースする"""
        result = {}

        lines = analysis_text.split('\n')
        for line in lines:
            if '商材/ブランド名' in line or '商材名' in line:
                result['product_name'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'メインターゲット' in line:
                result['target_audience'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'キャッチコピー' in line:
                result['catchphrase'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'ベネフィット1' in line:
                result['benefit1'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'ベネフィット2' in line:
                result['benefit2'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'オファー' in line:
                result['offer'] = line.split(':', 1)[1].strip() if ':' in line else ''
            elif 'CTAテキスト' in line or 'CTA' in line:
                result['cta_text'] = line.split(':', 1)[1].strip() if ':' in line else ''

        return result

    def _generate_video_prompt(self, product_info: Dict[str, str]) -> str:
        """
        商材情報を基に動画生成プロンプトを生成

        Args:
            product_info: 商材情報（7つの要素）

        Returns:
            動画生成用のプロンプト
        """
        product_name = product_info.get('product_name', '[商材/ブランド名]')
        target = product_info.get('target_audience', '[メインターゲット]')
        catchphrase = product_info.get('catchphrase', '[キャッチコピー]')
        benefit1 = product_info.get('benefit1', '[ベネフィット1]')
        benefit2 = product_info.get('benefit2', '[ベネフィット2]')
        offer = product_info.get('offer', '[オファー]')
        cta_text = product_info.get('cta_text', '[CTAテキスト]')

        prompt = f"""汎用P-MAX広告動画 生成プロンプト（12秒・キャラクター画像1点入力）
【目的】 Google P-MAX広告枠（YouTube Shorts, Discover等）向けに、無音再生でもターゲットの注意を引き、行動を喚起する12秒の動画を生成する。

【提供アセット（必須）】

キャラクター画像（背景透過推奨）

【ユーザー入力（URL分析結果）】

[商材/ブランド名]：{product_name}

[メインターゲット]：{target}

[キャッチコピー]：{catchphrase}

[ベネフィット1]：{benefit1}

[ベネフィット2]：{benefit2}

[オファー（任意）]：{offer}

[CTAテキスト]：{cta_text}

【AIへの動画生成シーケンス指示】

全体のトーン＆マナー: モダン、スピーディー、信頼感。BGMはアップテンポなインストルメンタル。テロップはすべて大きく、読みやすいゴシック体を使用し、背景と強いコントラストをつけること。

▼ シーケンス 1：掴み (0-3秒)

映像:

提供されたキャラクター画像を入力画像として使用する。

このキャラクターに、{target} に向かって手を振ったり、元気にジャンプして登場するようなアニメーション（動き）をつける。

背景はブランドカラーをベースにした明るくダイナミックな抽象アニメーション。

テロップ (特大): {catchphrase}

▼ シーケンス 2：ベネフィット 1 (4-6秒)

映像:

キャラクターは画面の隅（例：左下）に移動し、案内役として頷いたり、指をさしたりするリアクションをとる。

画面中央に {benefit1} を象徴するシンプルなアイコン（例：歯車、チェックマーク、書類アイコン）がポップアップ表示される。

テロップ (大・中央): {benefit1}

▼ シーケンス 3：ベネフィット 2 / オファー (7-9秒)

映像:

中央のアイコンとテキストが、{benefit2} または {offer} の内容に素早く切り替わる。（例：グラフアイコン、カレンダーアイコン）

キャラクターは驚きや喜びの表情のアニメーションをとる。

テロップ (大・中央): {benefit2} または {offer}

▼ シーケンス 4：CTAとブランド提示 (10-12秒)

映像:

画面全体が白またはブランドカラーのクリーンな背景に切り替わる。（キャラクターはここで消えても良い）

中央にテキストで {product_name} をロゴのように大きく表示する。（フォントは太く、信頼感のあるもの）

その下に、行動喚起のボタン風デザインを配置する。

テロップ (ボタン内・特大): {cta_text}

テロップ (画面下部・小): {product_name} で検索

共通事項:
- テキストが読みやすいように、最前面に配置し、背景と十分なコントラストを持たせること。
"""

        return prompt

    def _invoke_gemini(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Lambda経由でGeminiを呼び出してレスポンスを取得
        （GeminiClientクラスを使用）

        Args:
            prompt: 分析プロンプト
            model: 使用するモデル名（省略時はデフォルト）

        Returns:
            Geminiのレスポンステキスト
        """
        return self.gemini_client.invoke_gemini(prompt, model)
