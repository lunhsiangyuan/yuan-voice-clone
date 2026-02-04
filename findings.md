# Yuan Voice Clone - 研究發現

## TTS 方案比較

### 安全性評估

| 方案 | 資料去向 | 隱私風險 |
|------|---------|---------|
| 剪映 (CapCut) | 中國伺服器 | 高 |
| Edge-TTS | Microsoft 美國 | 中 |
| GPT-SoVITS | 本地硬碟 | 低(最安全) |

### ElevenLabs 模型比較

| 模型類型 | 訓練時長要求 | 品質 | 驗證需求 |
|---------|------------|------|---------|
| IVC (Instant) | 1 分鐘+ | 中等 | 無 |
| PVC (Professional) | 30+ 分鐘 | 高 | 需人工驗證 |

## 音檔分析

### 台灣癌症基金會專訪
- 時長: 17.4 分鐘
- 特點: 獨白式講解，無主持人干擾
- 品質: 適合直接訓練

### 新雲林之聲採訪
- 時長: 共 79.6 分鐘
- 特點: 對談形式，有主持人聲音
- 處理: 需要語音分離

## 語音分離工具

| 工具 | 用途 | 適用場景 |
|------|------|---------|
| Demucs | 音樂人聲分離 | 去背景音樂 |
| pyannote-audio | 講者分離 | 多人對話 |
| Whisper | 語音轉文字 | 標記時間軸 |

## ElevenLabs API 參數測試

已測試組合:
- eleven_multilingual_v2 + stability=0.5
- eleven_multilingual_v2 + stability=0.3, similarity=0.9
- eleven_turbo_v2_5
- eleven_flash_v2_5

結論: PVC 品質 > IVC，建議使用 PVC

## 更新記錄

- 2024-02-04: 初始發現整理

## GPT-SoVITS Mac 安裝發現

### 硬體規格
- Mac Mini M4 Pro + 64GB RAM
- 可運行 CPU 推理

### MPS 支援狀態
- ❌ 訓練: 不支援 Apple Silicon MPS
- ✅ 推理: 可用 CPU 運行
- 建議: 雲端 GPU 訓練 + 本地推理

### 安裝依賴
```
torch numpy scipy tensorboard librosa==0.9.2 numba==0.56.4
pytorch-lightning ffmpeg-python onnxruntime tqdm
cn2an pypinyin g2p_en chardet gradio transformers
psutil wordsegment jieba langdetect pyopenjtalk jaconv
opencc opencc-python-reimplemented
```

### 預訓練模型
- 來源: huggingface.co/lj1995/GPT-SoVITS
- 大小: ~2GB
- 包含: HuBERT, RoBERTa, HiFiGAN, SoVITS pretrained

### WebUI 配置
- 端口: 9876 (修改自原始 9874)
- 配置文件: config.py

### 工作流程
```
訓練 (雲端 GPU)           推理 (本地 CPU)
        │                        │
        ▼                        ▼
┌─────────────┐          ┌─────────────┐
│ Google Colab │────────▶│  Mac Mini   │
│ (訓練模型)   │ 下載模型 │ (WebUI推理) │
└─────────────┘          └─────────────┘
```

### 更新
- 2024-02-04: GPT-SoVITS 安裝完成

---

## 當前使用的 Voice Clone

### 袁倫祥醫師 PVC (推薦使用)
- **Voice ID**: `6ksMfqyR3w7UcA4bkv1N`
- **名稱**: 袁倫祥醫師_Clean
- **類型**: Professional Voice Clone (PVC)
- **狀態**: ✅ 可使用（fine-tuning 進行中，品質已達可用標準）
- **訓練資料**: 台灣癌症基金會專訪 (17 分鐘，乾淨單一講者)
- **語言**: Chinese (Mandarin Taiwan)
- **建議模型**: eleven_multilingual_v2

### API 使用範例
```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="YOUR_API_KEY")

audio = client.text_to_speech.convert(
    voice_id="6ksMfqyR3w7UcA4bkv1N",
    text="您的文字內容",
    model_id="eleven_multilingual_v2"
)
```

### 建議參數設定
- **Stability**: 0.7-0.8 (較穩定)
- **Similarity**: 0.8-0.9 (高相似度)
- **Style Exaggeration**: 0 (無誇張)
- **Speaker Boost**: ON

---

## 即時語音通話應用 (BlackHole 虛擬音源)

### 核心概念
```
AI 生成音檔 → BlackHole (虛擬麥克風) → Signal/Discord → 朋友聽到
```

### 所需軟體
| 軟體 | 用途 | 安裝方式 |
|------|------|----------|
| BlackHole 2ch | 虛擬音源線 | `brew install blackhole-2ch` |
| IINA / VLC | 指定音訊輸出的播放器 | `brew install iina` |
| 音訊 MIDI 設定 | Mac 內建，設定多重輸出 | Command + Space 搜尋 "MIDI" |

### 設定架構圖
```
┌─────────────────────────────────────────────────────────┐
│                    音訊 MIDI 設定                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐    ┌─────────────────────────┐    │
│  │ 多重輸出裝置     │    │ 聚集裝置 (進階)         │    │
│  │                 │    │                         │    │
│  │ ☑ BlackHole 2ch │    │ ☑ 實體麥克風            │    │
│  │ ☑ 耳機/揚聲器   │    │ ☑ BlackHole 2ch        │    │
│  │                 │    │                         │    │
│  │ 用途: 播放+監聽  │    │ 用途: 人聲+AI聲同時輸入 │    │
│  └─────────────────┘    └─────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Discord/Signal 設定
- **輸入裝置**: BlackHole 2ch (或聚集裝置)
- **輸出裝置**: 耳機 (不要選 BlackHole，避免回授)
- **關閉**: Krisp 雜訊抑制、回音消除

### 操作流程
1. ElevenLabs 生成音檔 (Voice ID: 6ksMfqyR3w7UcA4bkv1N)
2. 用 Signal/Discord 撥打電話
3. 用 IINA/VLC 播放音檔 (輸出設為多重輸出裝置)
4. 朋友聽到 AI 聲音

---

## ElevenLabs API 設定

### API Key
- **Key Name**: Allen
- **Key ID**: 結尾 `•0117`
- **儲存位置**: `~/.zshrc` (ELEVENLABS_API_KEY)

### 最佳語音參數
針對穩定、清晰的語音輸出：
```python
voice_settings={
    "stability": 0.95,        # 高穩定度，減少變化
    "similarity_boost": 0.90, # 高相似度
    "style": 0.0,             # 無風格誇張
    "use_speaker_boost": True # 開啟講者增強
}
```

### 快速生成語音指令
```bash
cd ~/Projects/yuan-voice-clone
python3 generate_test.py
open -a IINA test_voice.mp3
```
