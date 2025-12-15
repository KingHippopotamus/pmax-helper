"""
Gemini API (Lambda経由) を呼び出すクライアントクラス
PHPのChatGptClient.phpを参考に実装
"""
import os
import json
import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Lambda経由でGemini APIを呼び出すクライアント
    """

    # Lambda エンドポイント
    LAMBDA_URL = "https://trdj86n9c9.execute-api.ap-northeast-1.amazonaws.com/default/callGeminiAPI"

    # デフォルトモデル
    DEFAULT_MODEL = "gemini-2.5-flash"

    # タイムアウト設定（秒）
    TIMEOUT = 60

    def __init__(self, secret_key: Optional[str] = None):
        """
        Args:
            secret_key: Lambda Secret Key（環境変数から取得も可能、現状は不要）
        """
        self.secret_key = secret_key or os.getenv('LAMBDA_SECRET_KEY')

    def invoke_gemini(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Gemini APIにリクエストを送信してレスポンスを取得

        Args:
            prompt: Geminiに送信するプロンプト
            model: 使用するモデル名（省略時はデフォルトモデルを使用）

        Returns:
            Geminiのレスポンステキスト

        Raises:
            Exception: API呼び出しに失敗した場合
        """
        try:
            # リクエストペイロードを作成
            payload = {
                "prompt": prompt
            }

            # モデル名が指定されている場合は追加
            if model:
                payload["model"] = model

            logger.info(f"📡 Calling Gemini Lambda API...")
            logger.debug(f"Model: {model or self.DEFAULT_MODEL}")
            logger.debug(f"Prompt length: {len(prompt)} characters")

            # HTTPリクエストを送信
            response = requests.post(
                self.LAMBDA_URL,
                json=payload,
                timeout=self.TIMEOUT
            )

            # HTTPエラーをチェック
            response.raise_for_status()

            # レスポンスをパース
            result = response.json()
            logger.info(f"✅ Gemini response received")

            # レスポンスからテキストを抽出
            response_text = self._extract_response(result)

            logger.debug(f"Response length: {len(response_text)} characters")

            return response_text

        except requests.exceptions.Timeout:
            error_msg = f"Gemini API request timed out after {self.TIMEOUT} seconds"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Gemini API request failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error in Gemini API call: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            raise Exception(error_msg)

    def _extract_response(self, result: Dict) -> str:
        """
        Lambda関数のレスポンスからGeminiのテキストを抽出

        Args:
            result: Lambda関数のレスポンス

        Returns:
            Geminiのレスポンステキスト

        Raises:
            Exception: レスポンスのパースに失敗した場合
        """
        try:
            # Lambda関数のレスポンス形式を確認
            logger.debug(f"Response type: {type(result)}")

            # レスポンスが辞書型でbodyキーがある場合
            if isinstance(result, dict) and 'body' in result:
                body = result['body']

                # bodyが文字列の場合はJSONとしてパース
                if isinstance(body, str):
                    body = json.loads(body)

                # responseキーからテキストを取得
                response_text = body.get('response', '')

                if not response_text:
                    raise Exception("No 'response' field found in Lambda response body")

                return response_text

            # レスポンスが辞書型でresponseキーが直接ある場合
            elif isinstance(result, dict) and 'response' in result:
                return result['response']

            # その他の形式の場合はエラー
            else:
                logger.error(f"Unexpected response format: {result}")
                raise Exception(f"Unexpected response format from Lambda: {type(result)}")

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Lambda response JSON: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Failed to extract response from Lambda result: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    def invoke_gemini_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        リトライ機能付きでGemini APIを呼び出す

        Args:
            prompt: Geminiに送信するプロンプト
            model: 使用するモデル名
            max_retries: 最大リトライ回数

        Returns:
            Geminiのレスポンステキスト

        Raises:
            Exception: すべてのリトライが失敗した場合
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_retries}")
                return self.invoke_gemini(prompt, model)

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")

                # 最後の試行でない場合は少し待機
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # 指数バックオフ: 1秒、2秒、4秒...

        # すべてのリトライが失敗
        error_msg = f"All {max_retries} attempts failed. Last error: {str(last_error)}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)
