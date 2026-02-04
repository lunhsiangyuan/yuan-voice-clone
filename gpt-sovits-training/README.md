# GPT-SoVITS 訓練資料

## 目錄結構

```
gpt-sovits-training/
├── audio/              # 訓練音檔
├── logs/               # 訓練輸出
├── transcript.list     # 標註文件
└── README.md           # 本文件
```

## 訓練資料格式

GPT-SoVITS 標註格式 (.list):
```
音檔路徑|說話人名稱|語言|文字內容
```

範例:
```
audio/chunk_001.wav|袁倫祥|zh|大家好，我是台大雲林分院泌尿科袁倫祥醫師。
```

## 訓練步驟

### 方法 1: Google Colab (推薦)
1. 開啟 Colab: https://colab.research.google.com/github/RVC-Boss/GPT-SoVITS/blob/main/Colab-WebUI.ipynb
2. 上傳本目錄的 audio/ 和 transcript.list
3. 在 WebUI 中訓練

### 方法 2: 本地 WebUI
1. 開啟 GPT-SoVITS WebUI (http://localhost:9876)
2. 使用 "1-訓練集格式化工具" 處理資料
3. 開始訓練

## 音檔要求

- 格式: WAV (推薦) 或 MP3
- 採樣率: 16kHz 或更高
- 單聲道
- 每段 3-15 秒為佳

## 當前資料來源

- 台灣癌症基金會專訪 (17.4 分鐘)
- 乾淨單人錄音
