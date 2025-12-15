// API設定

// 環境変数からAPI URLを取得
// ローカル開発時は空文字（Vite proxyを使用）
// Colab使用時は VITE_API_URL を .env.local に設定
export const API_BASE_URL = import.meta.env.VITE_API_URL || ''

console.log('🔧 API_BASE_URL:', API_BASE_URL || 'Using Vite proxy (localhost:5001)')
