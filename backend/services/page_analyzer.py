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

            # キャラクター画像を抽出
            print("\n🖼️ キャラクター画像を抽出中...")
            from .scraper import ImageScraper
            scraper = ImageScraper(url)
            images = scraper.extract_images()
            character_image_url = images.get('character_url', '')
            print(f"✅ キャラクター画像URL: {character_image_url}")

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
                'page_url': url,  # URLを追加して、画像抽出で使用できるようにする
                'character_image_url': character_image_url  # キャラクター画像URLを追加
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

    def _generate_video_prompt(self, product_info: Dict[str, str], aspect_ratio: str = "16:9") -> str:
        """
        商材情報を基に動画生成プロンプトを生成

        Args:
            product_info: 商材情報（7つの要素）
            aspect_ratio: アスペクト比（"16:9", "9:16", "1:1"）

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

        # 1:1用の画面構成指示（正方形の時のみ追加）
        square_instruction = ""
        if aspect_ratio == "1:1":
            square_instruction = """
【画面構成の重要指定】
正方形（1:1）のアスペクト比を想定し、すべての重要なテキストとキャラクターのアクションは、画面の「中央部分（縦方向の中間エリア）」に集中させてください。上下の余白には重要な要素を配置しないでください。

"""

        prompt = f"""【動画生成指示】
SNS広告向けの12秒のショート動画を作成してください。
トーン＆マナーは、モダンでスピーディー、かつ信頼感のある雰囲気です。
BGMはアップテンポなインストルメンタルのみで、音声やナレーションは含めません。

{square_instruction}【入力画像について】
提供された画像は「ブランドのマスコットキャラクター（イラスト）」です。このマスコットをアニメーションさせてください。

【タイムラインと詳細指示】

● 0-3秒：オープニング
背景はブランドカラーを基調とした明るくダイナミックな抽象アニメーションです。
マスコットキャラクターが元気にジャンプ、または手を振りながら登場し、視聴者の注意を引きます。
画面中央に、太字のゴシック体で以下のテキストを大きく明瞭に表示してください。
テキスト：「{catchphrase}」

● 4-6秒：ベネフィット提示1
キャラクターは画面の隅（左下など）に移動し、案内役として頷いたり指差しを行います。
画面中央に、「{benefit1}」を象徴するシンプルなアイコン（歯車やチェックマークなど）がポップアップします。
中央に見やすく以下のテキストを表示してください。
テキスト：「{benefit1}」

● 7-9秒：ベネフィット提示2
中央のアイコンが、「{benefit2}」や「{offer}」をイメージさせるアイコン（グラフやカレンダーなど）に素早く切り替わります。
キャラクターは驚きや喜びの表情を見せます。
以下のテキストに切り替えてください。
テキスト：「{benefit2}」または「{offer}」

● 10-12秒：エンディング（CTA）
背景が白、またはクリーンな単色に切り替わります。
中央にロゴのように大きく「{product_name}」と表示します。
その下にボタン風のデザインを配置し、以下のテキストを含めます。
ボタン内テキスト：「{cta_text}」
画面下部テキスト：「{product_name} で検索」

【テキスト表示のルール】
すべてのテキストは太字のゴシック体を使用し、背景とのコントラストを強くして可読性を最優先してください。文字崩れがないようにレンダリングしてください。
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
