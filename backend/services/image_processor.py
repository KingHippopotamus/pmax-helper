from PIL import Image
from io import BytesIO
from typing import Tuple

class ImageProcessor:
    """画像の前処理を行うクラス"""

    # fal-ai/sora-2 が対応する解像度とアスペクト比
    # 一般的な動画のアスペクト比: 16:9
    DEFAULT_ASPECT_RATIO = (16, 9)
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720

    @staticmethod
    def preprocess_image(
        image_data: bytes,
        target_aspect_ratio: Tuple[int, int] = DEFAULT_ASPECT_RATIO,
        max_width: int = DEFAULT_WIDTH,
        max_height: int = DEFAULT_HEIGHT
    ) -> bytes:
        """
        画像を指定されたアスペクト比に調整（パディング追加）

        Args:
            image_data: 元画像のバイトデータ
            target_aspect_ratio: 目標のアスペクト比 (width, height)
            max_width: 最大幅
            max_height: 最大高さ

        Returns:
            処理済み画像のバイトデータ
        """
        img = Image.open(BytesIO(image_data))

        # RGBA に変換（透明背景対応）
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 目標のアスペクト比を計算
        target_ratio = target_aspect_ratio[0] / target_aspect_ratio[1]

        # 元画像のアスペクト比
        original_ratio = img.width / img.height

        # リサイズ後のサイズを計算
        if original_ratio > target_ratio:
            # 横長の画像 - 幅を基準にリサイズ
            new_width = min(img.width, max_width)
            new_height = int(new_width / target_ratio)
        else:
            # 縦長の画像 - 高さを基準にリサイズ
            new_height = min(img.height, max_height)
            new_width = int(new_height * target_ratio)

        # 元画像を目標サイズに収まるようにリサイズ（アスペクト比維持）
        img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)

        # 新しいキャンバスを作成（黒背景）
        canvas = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 255))

        # 元画像を中央に配置
        paste_x = (new_width - img.width) // 2
        paste_y = (new_height - img.height) // 2
        canvas.paste(img, (paste_x, paste_y), img)

        # RGB に変換（多くのAPIはRGBを要求）
        canvas = canvas.convert('RGB')

        # バイトデータに変換
        output = BytesIO()
        canvas.save(output, format='JPEG', quality=95)
        return output.getvalue()
