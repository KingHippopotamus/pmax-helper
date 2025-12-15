# Pmax Helper - AI Video Generator

Webページからヘッダーロゴとキャラクター画像を抽出し、AI（fal-ai/sora-2）を使って動画を生成するツールです。

## 機能

- 指定されたURLのWebページから特定の画像を抽出
- 抽出した画像を自動的に前処理（アスペクト比調整）
- fal-ai/sora-2 API を使用して各画像から動画を生成
  - **ロゴ画像**: エフェクト付きのカッコいいアニメーション
  - **キャラクター画像**: ダンスアニメーション
- 生成された動画をWebブラウザでプレビュー
- ZIPファイルで一括ダウンロード

## 技術スタック

### バックエンド
- Python 3.x
- Flask (Web API)
- BeautifulSoup4 (HTMLパース)
- Pillow (画像処理)
- fal-client (AI動画生成)

### フロントエンド
- React 18
- TypeScript
- Vite
- Axios

## セットアップ

### 1. リポジトリのクローン

```bash
cd pmax_helper
```

### 2. バックエンドのセットアップ

```bash
cd backend

# 仮想環境の作成（推奨）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env ファイルを編集して FAL_KEY を設定
```

### 3. API キーの取得

#### 3-1. fal-ai API キー（動画生成用）

1. [fal.ai](https://fal.ai/) にアクセス
2. アカウントを作成してログイン
3. Dashboard から API Key を取得
4. `backend/.env` ファイルに API Key を設定

```
FAL_KEY=your_actual_api_key_here
```

#### 3-2. Google Gemini API キー（ページ分析用）

1. [Google AI Studio](https://ai.google.dev/) にアクセス
2. Googleアカウントでログイン
3. 「Get API key」から API Key を取得
4. `backend/.env` ファイルに API Key を設定

```
LAMBDA_SECRET_KEY=your_gemini_api_key_here
```

**注意:** 両方のAPIキーが必要です。どちらか一方でも欠けていると機能が動作しません。

### 4. フロントエンドのセットアップ

```bash
cd ../frontend

# 依存関係のインストール
npm install
```

## 起動方法

### 方法1: 起動スクリプトを使用（推奨）

**ターミナル1 - バックエンド:**
```bash
./start-backend.sh
```

**ターミナル2 - フロントエンド:**
```bash
./start-frontend.sh
```

### 方法2: 手動で起動

**バックエンドサーバーの起動:**

```bash
cd backend
source venv/bin/activate  # 仮想環境をアクティベート
python3 app.py
```

サーバーは `http://localhost:5001` で起動します。

**注意:** macOSでポート5000がAirPlayレシーバーで使用されている場合があるため、ポート5001を使用しています。

**フロントエンドの起動（別のターミナルで）:**

```bash
cd frontend
npm run dev
```

フロントエンドは `http://localhost:3000` で起動します。

## 使い方

1. ブラウザで `http://localhost:3000` を開く
2. ページのURLを入力欄に貼り付け
3. 「🎬 動画を生成」ボタンをクリック
4. 生成が完了すると、2つの動画がプレビュー表示される
5. 「📥 ZIPでダウンロード」ボタンで動画をダウンロード

## 抽出される画像

このツールは以下のCSSセレクタで画像を抽出します：

### ヘッダーロゴ
```css
.wonder-header .wonder-header-inner .wonder-header-logo-wrapper .wonder-header-main .wonder-header-logo img
```

### キャラクター画像
```css
.wonder-cv .wonder-cv-wrapper .wonder-cv-back-person-img
```

※ 対象のWebページにこれらの要素が存在しない場合、画像は抽出されません。

## API エンドポイント

### POST /api/extract-images
指定されたURLから画像URLを抽出します。

**リクエスト:**
```json
{
  "page_url": "https://example.com"
}
```

**レスポンス:**
```json
{
  "logo_url": "https://example.com/logo.png",
  "character_url": "https://example.com/character.png"
}
```

### POST /api/generate-videos
画像を抽出して動画を生成します。

**リクエスト:**
```json
{
  "page_url": "https://example.com"
}
```

**レスポンス:**
```json
{
  "logo_video": {
    "video_url": "https://...",
    "status": "success"
  },
  "character_video": {
    "video_url": "https://...",
    "status": "success"
  }
}
```

### POST /api/download-videos
生成された動画をZIPファイルでダウンロードします。

**リクエスト:**
```json
{
  "logo_video_url": "https://...",
  "character_video_url": "https://..."
}
```

**レスポンス:**
ZIPファイル（バイナリ）

## トラブルシューティング

### 画像が抽出されない
- 指定したURLが正しいか確認してください
- ページの構造が変更されている可能性があります
- CSSセレクタが一致しない場合は、`backend/services/scraper.py` を修正してください

### 動画生成に失敗する
- fal-ai API キーが正しく設定されているか確認してください
- API の利用制限に達していないか確認してください
- インターネット接続を確認してください

### CORS エラー
- バックエンドとフロントエンドが正しいポートで起動しているか確認してください
- バックエンド: `http://localhost:5000`
- フロントエンド: `http://localhost:3000`

## ライセンス

MIT

## 開発者向け

### ディレクトリ構造

```
pmax_helper/
├── backend/
│   ├── app.py                 # Flask APIサーバー
│   ├── requirements.txt       # Python依存関係
│   ├── .env.example          # 環境変数サンプル
│   └── services/
│       ├── scraper.py        # 画像抽出
│       ├── image_processor.py # 画像前処理
│       └── video_generator.py # fal-ai統合
├── frontend/
│   ├── package.json          # Node.js依存関係
│   ├── vite.config.ts        # Vite設定
│   ├── tsconfig.json         # TypeScript設定
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── App.css
│       ├── main.tsx
│       └── components/
│           ├── VideoGenerator.tsx
│           └── VideoGenerator.css
└── README.md
```

### カスタマイズ

#### 動画生成プロンプトの変更

`backend/services/video_generator.py` の以下のメソッドを編集：
- `generate_logo_video()`: ロゴ動画のプロンプト
- `generate_character_video()`: キャラクター動画のプロンプト

#### CSSセレクタの変更

`backend/services/scraper.py` の以下のメソッドを編集：
- `_extract_logo()`: ロゴ画像のセレクタ
- `_extract_character()`: キャラクター画像のセレクタ

#### アスペクト比の変更

`backend/services/image_processor.py` のクラス変数を編集：
- `DEFAULT_ASPECT_RATIO`: 目標アスペクト比
- `DEFAULT_WIDTH`: 最大幅
- `DEFAULT_HEIGHT`: 最大高さ

---

## Google Colabでの起動方法（推奨）

Python環境の構築が不要で、誰でも簡単に起動できます。

### 起動手順

1. **Colabでノートブックを開く**
   - 直接リンク: https://colab.research.google.com/github/KingHippopotamus/pmax-helper/blob/main/pmax_helper_colab.ipynb
   - または Google Colab で「GitHub」タブから `KingHippopotamus/pmax-helper` を検索

2. **API KEYを設定（Google Colab Secrets機能を使用）**
   - 左サイドバーの **🔑 鍵アイコン（Secrets）** をクリック
   - 以下の3つのシークレットを追加:
     - **名前**: `FAL_KEY` → **値**: あなたのfal.ai APIキー
     - **名前**: `LAMBDA_SECRET_KEY` → **値**: ダミー値（例: `dummy_key`）
     - **名前**: `NGROK_AUTH_TOKEN` → **値**: あなたのngrok認証トークン
   - 各シークレットの「ノートブックからアクセスを許可」をONにする

   ⚠️ **重要**: Secrets機能を使うことで、APIキーがノートブックに露出せず安全です

   **ngrok認証トークンの取得方法:**
   1. https://dashboard.ngrok.com/signup にアクセス
   2. 無料アカウントを作成（GoogleアカウントでOK）
   3. https://dashboard.ngrok.com/get-started/your-authtoken から認証トークンをコピー

3. **セルを順番に実行**
   - 上から順番にすべてのセルを実行
   - ngrok URLが表示されます（例: `https://xxxx.ngrok-free.app`）

4. **フロントエンドを起動**
   - ローカル環境で以下を実行:
   ```bash
   cd frontend
   echo 'VITE_API_URL=https://xxxx.ngrok-free.app' > .env.local
   npm run dev
   ```
   - ブラウザで `http://localhost:3000` を開く

### 注意事項

- **セッションタイムアウト**: 90分無操作で切断、最大12時間
- **ngrok URLの変更**: 再起動のたびにURLが変わるため、フロントエンドの `.env.local` を更新してください
- **無料枠**: Google Colabの無料枠で十分動作します

### トラブルシューティング

#### セッションが切れた
- ノートブックを最初から再実行
- 新しいngrok URLをフロントエンドに設定

#### CORS エラー
- バックエンドが正しく起動しているか確認
- ngrok URLが正しく設定されているか確認

#### パッケージインストールエラー
- Colabを再起動して最初からやり直す
