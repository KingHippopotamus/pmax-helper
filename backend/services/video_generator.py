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

    def trim_video(self, video_url: str, start_time: float = 0.3, square_crop: bool = False) -> bytes:
        """
        動画をトリミング（開始時間カット + オプションで正方形クロップ）

        Args:
            video_url: トリミングする動画のURL
            start_time: 開始時間（秒）。この時間以降の動画を使用
            square_crop: Trueの場合、中央を正方形にクロップ

        Returns:
            トリミング後の動画のバイトデータ
        """
        import tempfile
        import os
        from moviepy.editor import VideoFileClip

        # 動画をダウンロード
        response = requests.get(video_url, timeout=60)
        response.raise_for_status()

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_input:
            tmp_input.write(response.content)
            input_path = tmp_input.name

        try:
            # moviepyで動画を読み込み
            clip = VideoFileClip(input_path)

            # 開始時間以降を切り出し
            if start_time > 0:
                clip = clip.subclip(start_time)

            # 正方形クロップが必要な場合
            if square_crop:
                width, height = clip.size
                square_size = min(width, height)
                x_center = width / 2
                y_center = height / 2
                x1 = x_center - square_size / 2
                y1 = y_center - square_size / 2
                clip = clip.crop(x1=x1, y1=y1, width=square_size, height=square_size)

            # 一時ファイルに書き出し
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_output:
                output_path = tmp_output.name

            clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                remove_temp=True,
                logger=None
            )

            # トリミング後の動画を読み込み
            with open(output_path, 'rb') as f:
                video_data = f.read()

            # クリーンアップ
            clip.close()
            os.unlink(input_path)
            os.unlink(output_path)

            return video_data

        except Exception as e:
            if os.path.exists(input_path):
                os.unlink(input_path)
            raise Exception(f"Failed to trim video: {str(e)}")

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
            aspect_ratio: アスペクト比（"16:9", "9:16", または "1:1"）

        Returns:
            動画生成結果
        """
        if not prompt:
            prompt = "Make this character dance with lively and fun movements. Add energetic body language and natural motion."

        # 1:1の場合は9:16で生成
        actual_ratio = "9:16" if aspect_ratio == "1:1" else aspect_ratio

        # 動画生成
        result = self.generate_video_from_image(
            image_data,
            prompt=prompt,
            duration=12,
            aspect_ratio=actual_ratio
        )

        if 'error' in result:
            return result

        # ポストプロセス: 最初0.3秒トリミング + 1:1の場合は正方形クロップ
        print("✂️ 動画をトリミング中...")
        try:
            video_url = result.get('video_url')
            square_crop = (aspect_ratio == "1:1")

            if square_crop:
                print("   - 最初0.3秒をカット")
                print("   - 中央を正方形にクロップ")
            else:
                print("   - 最初0.3秒をカット")

            trimmed_video_data = self.trim_video(
                video_url,
                start_time=0.3,
                square_crop=square_crop
            )

            return {
                'video_data': trimmed_video_data,
                'status': 'success',
                'trimmed': True
            }
        except Exception as e:
            logger.error(f"❌ Video trimming failed: {str(e)}")
            raise VideoGenerationError(f"Failed to trim video: {str(e)}")
