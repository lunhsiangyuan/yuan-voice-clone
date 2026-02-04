# Yuan Voice Clone 專案規劃

## 目標
建立袁倫祥醫師的高品質聲音模型，支援多種 TTS 應用場景

## 目前狀態

ElevenLabs Voice Models:
- IVC (Instant Clone): 完成 - Voice ID: Z1EU1IiJ7plOOioojpGN
- PVC (Professional): 待驗證 - Voice ID: 6ksMfqyR3w7UcA4bkv1N

GPT-SoVITS:
- 安裝狀態: 完成
- WebUI 端口: 9876
- 設備: CPU (Mac Mini M4 Pro)

## 音檔資源

| 來源 | 狀態 | 品質 |
|------|------|------|
| 台灣癌症基金會專訪 (17.4分鐘) | 已分割上傳 (6 chunks) | 乾淨單人 |
| 新雲林之聲 #1 (39.8分鐘) | 待分離 | 混音(主持人+醫師) |
| 新雲林之聲 #2 (39.8分鐘) | 待分離 | 混音(主持人+醫師) |

## Phases

### Phase 1: ElevenLabs PVC 驗證 - in_progress
- [x] 建立 Clean PVC (6ksMfqyR3w7UcA4bkv1N)
- [x] 上傳乾淨音檔 (台灣癌症基金會)
- [ ] 通過聲音驗證
- [ ] 測試 PVC 輸出品質

### Phase 2: 聲音分離 (雲林之聲) - pending
- [ ] 分離 新雲林之聲_1090703 音檔
- [ ] 分離 新雲林之聲_攝護腺常見疾病 音檔
- [ ] 驗證分離品質

### Phase 3: GPT-SoVITS 本地設置 - complete
- [x] 安裝 GPT-SoVITS
- [x] 下載預訓練模型
- [x] WebUI 啟動成功 (port 9876)
- [ ] 準備訓練資料格式
- [ ] 本地訓練聲音模型 (需雲端 GPU)
- [ ] 推理測試

### Phase 4: TTS 整合應用 - pending
- [ ] Edge-TTS 腳本 (衛教/迷因)
- [ ] GPT-SoVITS 推理腳本
- [ ] 自動化工作流程

## 重要發現

GPT-SoVITS Mac 限制:
- MPS (Apple GPU) 不支援
- 訓練需要 NVIDIA GPU (建議用 Google Colab)
- 推理可用 CPU 運行

## 更新記錄

- 2024-02-04 20:35: GPT-SoVITS WebUI 啟動成功
- 2024-02-04 20:23: 預訓練模型下載完成
- 2024-02-04 20:18: GPT-SoVITS 安裝開始
- 2024-02-04 20:15: 建立規劃文件
- 2024-02-04 20:14: 新增 TTS 方案選擇指南
