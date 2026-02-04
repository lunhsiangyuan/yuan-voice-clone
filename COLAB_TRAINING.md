# GPT-SoVITS Colab 訓練指南

## 快速開始

### 方法 1: 使用官方 Colab (推薦)

1. 開啟官方 Colab:
   https://colab.research.google.com/github/RVC-Boss/GPT-SoVITS/blob/main/Colab-WebUI.ipynb

2. 設定 GPU:
   - Runtime > Change runtime type > GPU (T4)

3. 執行環境設置 cells

4. 上傳訓練資料:
   - 上傳 `gpt-sovits-training/yuan_training_data.zip`
   - 在 Colab 中解壓縮

5. 使用 WebUI 訓練

### 方法 2: 使用本專案 Notebook

1. 上傳 `colab_training.ipynb` 到 Google Colab
2. 依照步驟執行

## 訓練資料

```
yuan_training_data.zip (18MB)
├── audio/                    # 252 個 WAV 音檔
│   ├── segment_000.wav
│   ├── segment_001.wav
│   └── ...
└── transcript_corrected.list # 標註文件
```

### 標註格式
```
音檔路徑|講者名稱|語言|文字內容
audio/segment_000.wav|袁倫祥|zh|大家好 我是台大雲林分院
```

## WebUI 訓練步驟

### Step 1: 資料預處理
1. 在 WebUI 中選擇「0-前處理-ASR」
2. 輸入訓練資料路徑
3. 選擇語言: 中文
4. 開始預處理

### Step 2: 訓練 GPT 模型
1. 選擇「1-GPT訓練」頁籤
2. 設定參數:
   - Epochs: 15-20
   - Batch size: 4-8
   - 學習率: 預設
3. 開始訓練

### Step 3: 訓練 SoVITS 模型
1. 選擇「1-SoVITS訓練」頁籤
2. 設定參數:
   - Epochs: 10-15
3. 開始訓練

### Step 4: 測試推理
1. 選擇「1-推理」頁籤
2. 載入訓練好的模型
3. 輸入參考音檔和測試文字
4. 生成語音

## 訓練參數建議

| 參數 | 建議值 | 說明 |
|------|--------|------|
| GPT Epochs | 15-20 | 資料量少時可增加 |
| SoVITS Epochs | 10-15 | - |
| Batch Size | 4-8 | 根據 GPU 記憶體調整 |
| 學習率 | 預設 | 不建議修改 |

## 輸出模型

訓練完成後會產生:
- `GPT_weights/袁倫祥-*.ckpt` - GPT 模型
- `SoVITS_weights/袁倫祥_*.pth` - SoVITS 模型

下載這些檔案到本地 Mac Mini 的 GPT-SoVITS 目錄即可使用。

## 注意事項

1. **GPU 限制**: Colab 免費版有使用時間限制，建議一次完成訓練
2. **資料備份**: 訓練前確保資料已上傳完成
3. **模型下載**: 訓練完成後立即下載模型，避免 session 超時遺失

## 故障排除

### 問題: CUDA out of memory
- 減少 batch size
- 使用較小的模型版本

### 問題: 訓練中斷
- 重新連接 Colab
- 從 checkpoint 繼續訓練

### 問題: 推理品質不佳
- 增加訓練 epochs
- 檢查標註文字是否正確
- 使用更多訓練資料
