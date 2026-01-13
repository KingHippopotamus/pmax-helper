#!/usr/bin/env python3
"""
FAL_KEY の動作確認スクリプト
"""
import os
from dotenv import load_dotenv
import fal_client

# .env ファイルを読み込む
load_dotenv()

# 環境変数を確認
fal_key = os.getenv('FAL_KEY')
print(f"FAL_KEY from .env: {fal_key[:20]}..." if fal_key else "❌ FAL_KEY not found")

# 画像URLを使って簡単なテスト
test_image_url = "https://adbase-static-prod.s3.ap-northeast-1.amazonaws.com/lp/upload/3253/544434e5d0cf5437b978412fa10cc279.png"

print(f"\n🧪 Testing fal-ai/sora-2/image-to-video API...")
print(f"Image URL: {test_image_url}")

try:
    result = fal_client.subscribe(
        "fal-ai/sora-2/image-to-video/pro",
        arguments={
            "image_url": test_image_url,
            "prompt": "Test animation",
            "duration": 4,  # 許可される値: 4, 8, 12
        },
        with_logs=True
    )

    print(f"\n✅ Success! Result:")
    print(result)

except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nError type: {type(e).__name__}")
