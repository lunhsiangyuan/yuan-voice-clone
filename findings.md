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
