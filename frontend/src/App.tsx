import React from 'react'
import VideoGenerator from './components/VideoGenerator'
import './App.css'

function App() {
  return (
    <div className="App">
      <header>
        <h1>🎬 Pmax Helper - AI Video Generator</h1>
        <p>Webページから画像を抽出してAI動画を生成</p>
      </header>
      <main>
        <VideoGenerator />
      </main>
    </div>
  )
}

export default App
