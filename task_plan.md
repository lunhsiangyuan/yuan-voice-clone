# Yuan Voice Clone 專案規劃

## 目標
建立袁倫祥醫師的高品質聲音模型，支援多種 TTS 應用場景

## 目前狀態

ElevenLabs Voice Models:
- IVC (Instant Clone): 完成 - Voice ID: Z1EU1IiJ7plOOioojpGN
- PVC (Professional): 待驗證 - Voice ID: 6ksMfqyR3w7UcA4bkv1N

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
- [ ] 安裝 pyannote-audio 或 Demucs
- [ ] 分離 新雲林之聲_1090703 音檔
- [ ] 分離 新雲林之聲_攝護腺常見疾病 音檔
- [ ] 驗證分離品質
- [ ] 補充上傳至 PVC (若需要更多音檔)

### Phase 3: GPT-SoVITS 本地設置 - pending
- [ ] 安裝 GPT-SoVITS
- [ ] 準備訓練資料格式
- [ ] 本地訓練聲音模型
- [ ] 斷網運行測試

### Phase 4: TTS 整合應用 - pending
- [ ] Edge-TTS 腳本 (衛教/迷因)
- [ ] GPT-SoVITS 推理腳本
- [ ] 自動化工作流程

## 已知問題

| 問題 | 狀態 | 解決方案 |
|------|------|---------|
| IVC 中文口音不自然 | 已識別 | 使用 PVC 替代 |
| 雲林之聲有主持人聲音 | 待處理 | 需要語音分離 |
| PVC 驗證失敗 | 已修正 | 改用乾淨音檔重建 |

## 更新記錄

- 2024-02-04 20:15: 建立規劃文件
- 2024-02-04 20:14: 新增 TTS 方案選擇指南
- 2024-02-04 20:09: 建立 Clean PVC
