"""
カスタム例外クラス
"""


class ContentPolicyViolationError(Exception):
    """
    Content policy violation error

    動画生成APIがコンテンツポリシー違反を検出した場合に発生する例外
    """
    pass


class VideoGenerationError(Exception):
    """
    Video generation error

    動画生成に失敗した場合の汎用的な例外
    """
    pass
