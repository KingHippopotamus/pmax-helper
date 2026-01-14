import fal_client
import os
import requests
import logging
from typing import Dict, Optional
from io import BytesIO
from .exceptions import ContentPolicyViolationError, VideoGenerationError

logger = logging.getLogger(__name__)

class VideoGenerator:
    """fal-ai を使用して画像から動画を生成するクラス"""

    def __init__(self, fal_key: Optional[str] = None):
        """
        Args:
            fal_key: fal.ai API キー（環境変数 FAL_KEY から取得も可能）
        """
        # FAL_KEY を環境変数に設定（fal_client が自動的に使用）
        if fal_key:
            os.environ['FAL_KEY'] = fal_key
    def generate_video_from_image(
        self,
        image_data: bytes,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9"
    ) -> Dict[str, any]:
        """
        画像から動画を生成 (Sora 2使用)

        Args:
            image_data: 入力画像のバイトデータ
            prompt: 動画生成のプロンプト（必須）
            duration: 動画の長さ（4, 8, または 12秒）
            aspect_ratio: アスペクト比（"16:9" または "9:16"）

        Returns:
            {
                'video_url': str,
                'status': str
            }
        """
        try:
            # 画像をアップロード
            image_url = self._upload_image(image_data)

            # fal-ai/sora-2/image-to-video を呼び出し
            # FAL_KEY は環境変数から fal_client が自動的に読み込む
            model_name = "fal-ai/sora-2/image-to-video/pro"
            print(f"🎯 使用モデル: {model_name}")

            result = fal_client.subscribe(
                model_name,
                arguments={
                    "image_url": image_url,
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": "auto",
                    "aspect_ratio": aspect_ratio
                },
                with_logs=True
            )

            print(f"✅ fal-ai result: {result}")

            # 結果から動画URLを取得
            video_url = result.get('video', {}).get('url')

            if not video_url:
                raise Exception(f"Video URL not found in response. Full response: {result}")

            return {
                'video_url': video_url,
                'status': 'success'
            }

        except Exception as e:
            error_message = str(e).lower()

            # Content policy violationエラーを検出
            if any(keyword in error_message for keyword in [
                'content policy',
                'policy violation',
                'nsfw',
                'not safe for work',
                'inappropriate content',
                'safety filter',
                'safety system'
            ]):
                logger.error(f"❌ Content policy violation detected: {str(e)}")
                raise ContentPolicyViolationError(
                    "動画生成がコンテンツポリシー違反により拒否されました。"
                    "人物画像の場合、服装や背景が原因の可能性があります。"
                    "より一般的な画像を使用するか、別の画像をお試しください。"
                )

            # その他のエラー
            logger.error(f"❌ Video generation failed: {str(e)}")
            raise VideoGenerationError(f"Failed to generate video: {str(e)}")

    def _upload_image(self, image_data: bytes) -> str:
        """
        画像を fal-ai にアップロードして URL を取得

        Args:
            image_data: 画像のバイトデータ

        Returns:
            アップロードされた画像のURL
        """
        try:
            # fal_client のファイルアップロード機能を使用
            print(f"📤 Uploading image ({len(image_data)} bytes)...")
            upload_result = fal_client.upload(
                image_data,
                "image/jpeg"
            )
            print(f"✅ Upload result: {upload_result}")
            return upload_result
        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")

    def download_video(self, video_url: str) -> bytes:
        """
        生成された動画をダウンロード

        Args:
            video_url: 動画のURL

        Returns:
            動画のバイトデータ
        """
        try:
            response = requests.get(video_url, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")

    def generate_logo_video(self, image_data: bytes) -> Dict[str, any]:
        """
        ロゴ用の動画を生成

        Args:
            image_data: ロゴ画像のバイトデータ

        Returns:
            動画生成結果
        """
        prompt = "Animate this logo with cool, dynamic effects while keeping the core design intact. Add subtle lighting changes, particle effects, or a sleek reveal."
        return self.generate_video_from_image(image_data, prompt=prompt, duration=4)

    def generate_character_video(self, image_data: bytes, prompt: Optional[str] = None, aspect_ratio: str = "16:9") -> Dict[str, any]:
        """
        キャラクター用の動画を生成

        Args:
            image_data: キャラクター画像のバイトデータ
            prompt: カスタムプロンプト（未指定の場合はデフォルト使用）
            aspect_ratio: アスペクト比（"16:9" または "9:16"）

        Returns:
            動画生成結果
        """
        if not prompt:
            prompt = "Make this character dance with lively and fun movements. Add energetic body language and natural motion."
        return self.generate_video_from_image(image_data, prompt=prompt, duration=12, aspect_ratio=aspect_ratio)
