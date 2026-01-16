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
        aspect_ratio: str = "16:9",
        max_retries: int = 1
    ) -> Dict[str, any]:
        """
        画像から動画を生成 (Sora 2使用)

        Args:
            image_data: 入力画像のバイトデータ
            prompt: 動画生成のプロンプト（必須）
            duration: 動画の長さ（4, 8, または 12秒）
            aspect_ratio: アスペクト比（"16:9" または "9:16"）
            max_retries: コンテンツポリシー違反時の最大リトライ回数（デフォルト: 1）

        Returns:
            {
                'video_url': str,
                'status': str
            }
        """
        # 画像を1回だけアップロード（リトライ時に再利用）
        image_url = self._upload_image(image_data)

        # リトライループ
        for attempt in range(max_retries):
            try:
                # fal-ai/sora-2/image-to-video を呼び出し
                # FAL_KEY は環境変数から fal_client が自動的に読み込む
                model_name = "fal-ai/sora-2/image-to-video/pro"

                if attempt > 0:
                    print(f"🔄 リトライ {attempt}/{max_retries - 1} 回目...")
                else:
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

                if attempt > 0:
                    print(f"✅ リトライ成功！（{attempt + 1}回目の試行で成功）")

                return {
                    'video_url': video_url,
                    'status': 'success'
                }

            except Exception as e:
                # fal.aiエラーをパース
                parsed_error = self._parse_fal_error(e)
                error_type = parsed_error['type']
                error_msg = parsed_error['msg']

                # エラータイプ別にハンドリング
                if error_type == 'content_policy_violation':
                    logger.error(f"❌ Content policy violation detected (attempt {attempt + 1}/{max_retries}): {error_msg}")

                    # 最後の試行でもエラーの場合は例外を投げる
                    if attempt == max_retries - 1:
                        logger.error(f"❌ {max_retries}回のリトライ後もコンテンツポリシー違反エラーが継続")
                        raise ContentPolicyViolationError(
                            f"動画生成がコンテンツポリシー違反により拒否されました（{max_retries}回試行）。\n"
                            "以下の理由が考えられます:\n"
                            "・画像に不適切なコンテンツが含まれている可能性\n"
                            "・プロンプトに不適切な表現が含まれている可能性\n"
                            "・人物画像の場合、服装や背景が原因の可能性\n\n"
                            "対処方法:\n"
                            "・より一般的な画像を使用してください\n"
                            "・別のキャラクター画像をお試しください\n"
                            "・プロンプト内容を確認してください"
                        )

                    # まだリトライ可能な場合は次のループへ
                    print(f"⚠️ コンテンツポリシー違反を検出。リトライします... ({attempt + 1}/{max_retries})")
                    continue

                # その他のエラー（リトライしない）
                logger.error(f"❌ Video generation failed: {error_msg}")
                raise VideoGenerationError(f"動画生成に失敗しました: {error_msg}")

        # ここには到達しないはずだが、念のため
        raise VideoGenerationError("予期しないエラー: リトライループが完了しましたが結果がありません")

    def _parse_fal_error(self, exception: Exception) -> dict:
        """
        fal.ai APIのエラーをパースして構造化データを取得

        Args:
            exception: fal.ai APIから返された例外

        Returns:
            {
                'type': str,  # エラータイプ (e.g., 'content_policy_violation')
                'msg': str,   # エラーメッセージ
                'details': dict  # その他の詳細情報
            }
        """
        import json

        error_str = str(exception)

        # JSON配列としてパースを試みる
        try:
            # "[{...}]" 形式の文字列をパース
            if error_str.startswith('[') and error_str.endswith(']'):
                error_list = json.loads(error_str)
                if error_list and isinstance(error_list, list):
                    # 最初のエラーオブジェクトを使用
                    first_error = error_list[0]
                    return {
                        'type': first_error.get('type', ''),
                        'msg': first_error.get('msg', ''),
                        'details': first_error
                    }
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

        # パース失敗時は文字列から推測
        error_lower = error_str.lower()

        # 'type': 'content_policy_violation' のパターンを探す
        if 'content_policy_violation' in error_lower or \
           ('content' in error_lower and 'policy' in error_lower):
            return {
                'type': 'content_policy_violation',
                'msg': error_str,
                'details': {}
            }

        # その他のエラー
        return {
            'type': 'unknown',
            'msg': error_str,
            'details': {}
        }

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

    def add_letterbox_to_square(self, video_url: str, start_time: float = 0.3) -> bytes:
        """
        横長動画の上下に黒い背景を追加して正方形にする

        Args:
            video_url: 動画のURL
            start_time: 開始時間（秒）。この時間以降の動画を使用

        Returns:
            正方形動画のバイトデータ
        """
        import tempfile
        import os
        from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip

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

            # 動画のサイズを取得
            width, height = clip.size

            # 正方形のサイズを決定（幅に合わせる）
            square_size = width

            # 黒い背景を作成
            background = ColorClip(
                size=(square_size, square_size),
                color=(0, 0, 0),
                duration=clip.duration
            )

            # 動画を中央に配置
            y_offset = (square_size - height) // 2
            clip = clip.set_position(('center', y_offset))

            # 背景と動画を合成
            final_clip = CompositeVideoClip([background, clip])

            # 一時ファイルに書き出し
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_output:
                output_path = tmp_output.name

            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                remove_temp=True,
                logger=None
            )

            # 処理後の動画を読み込み
            with open(output_path, 'rb') as f:
                video_data = f.read()

            # クリーンアップ
            clip.close()
            final_clip.close()
            background.close()
            os.unlink(input_path)
            os.unlink(output_path)

            return video_data

        except Exception as e:
            if os.path.exists(input_path):
                os.unlink(input_path)
            raise Exception(f"Failed to add letterbox: {str(e)}")

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

        video_url = result.get('video_url')

        # ポストプロセス
        try:
            if aspect_ratio == "1:1":
                # 1:1の場合: 縦長動画の中央を正方形にクロップ
                print("✂️ 動画をトリミング中...")
                print("   - 最初0.3秒をカット")
                print("   - 中央を正方形にクロップ")

                trimmed_video_data = self.trim_video(
                    video_url,
                    start_time=0.3,
                    square_crop=True
                )

                return {
                    'video_data': trimmed_video_data,
                    'status': 'success',
                    'trimmed': True
                }
            else:
                # 16:9, 9:16の場合: 最初0.3秒のみトリミング
                print("✂️ 動画をトリミング中...")
                print("   - 最初0.3秒をカット")

                trimmed_video_data = self.trim_video(
                    video_url,
                    start_time=0.3,
                    square_crop=False
                )

                return {
                    'video_data': trimmed_video_data,
                    'status': 'success',
                    'trimmed': True
                }
        except Exception as e:
            logger.error(f"❌ Video post-processing failed: {str(e)}")
            raise VideoGenerationError(f"動画の後処理に失敗しました: {str(e)}")
