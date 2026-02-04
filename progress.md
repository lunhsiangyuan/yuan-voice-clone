# Yuan Voice Clone - 進度記錄

## Session Log

### 2024-02-04 Session 1 (earlier)

**完成項目:**
1. 建立 ElevenLabs IVC 聲音模型
2. 測試多種 TTS 參數組合
3. 建立 PVC 但驗證失敗(混音問題)
4. 分析發現台灣癌症基金會音檔較乾淨
5. 分割台灣癌症基金會音檔 (6 chunks)
6. 刪除混音 PVC
7. 建立 Clean PVC (6ksMfqyR3w7UcA4bkv1N)

**遇到問題:**
- IVC 中文口音不自然
- 雲林之聲音檔有主持人聲音導致驗證失敗

### 2024-02-04 Session 2 (current)

**完成項目:**
1. 新增 TTS 方案選擇指南到 README
2. 建立專案規劃文件

**下一步:**
- Phase 1: 完成 PVC 聲音驗證
- Phase 2: 分離雲林之聲音檔
- Phase 3: 設置 GPT-SoVITS 本地環境

## Files Created/Modified

| 檔案 | 狀態 | 說明 |
|------|------|------|
| README.md | 已更新 | 新增 TTS 方案選擇指南 |
| task_plan.md | 新建 | 專案規劃 |
| findings.md | 新建 | 研究發現 |
| progress.md | 新建 | 進度記錄 |
| clean_chunks/*.mp3 | 已建立 | 6 個乾淨音檔片段 |
| pvc_clean_voice_id.txt | 已建立 | Clean PVC 資訊 |

## Voice IDs

- IVC: Z1EU1IiJ7plOOioojpGN
- PVC Clean: 6ksMfqyR3w7UcA4bkv1N (pending verification)

**20:25** - PVC 狀態檢查
- 目前已上傳 17 分鐘音檔 (6 個 chunks)
- ElevenLabs 建議至少 30 分鐘（Good）、1 小時（Better）、2 小時（Best）
- 需要額外 13+ 分鐘音檔才能達到 Good 等級

**20:26** - 雲林之聲音檔分析
- Whisper 轉錄完成 (1795 個片段)
- 音檔為主持人和袁醫師的對話
- Voice Isolator 無法分離不同講者（只能去背景噪音）
- 需要使用 Speaker Diarization 或手動標記

---

## 下一步選項

### Option A: 先驗證再訓練（17 分鐘）
- 用現有 17 分鐘音檔完成驗證
- 先看初步效果，之後再添加更多音檔

### Option B: 手動標記雲林之聲
- 聽錄音識別袁醫師發言時間段
- 用 ffmpeg 切割出乾淨片段
- 上傳後再驗證

### Option C: 使用 pyannote-audio 自動分離
- 安裝 Speaker Diarization 工具
- 自動識別不同講者
- 提取袁醫師的發言片段

**20:30** - PVC 訓練狀態確認
- ✅ 聲音驗證已通過
- ✅ PVC 訓練正在進行中 (fine-tuning)
- ⏳ 等待訓練完成（ElevenLabs 會發送通知）
- ❌ 訓練完成前無法使用此 voice

**錯誤訊息**: "The voice with voice_id 6ksMfqyR3w7UcA4bkv1N is not fine-tuned and thus cannot be used."

---

## 專案狀態總結

### 已完成
1. ✅ 專案設置 (GitHub repo, 目錄結構)
2. ✅ 音檔分析與處理
3. ✅ 建立乾淨 PVC (17 分鐘音檔)
4. ✅ 聲音驗證通過
5. ✅ PVC 訓練已提交

### 進行中
- 🔄 ElevenLabs PVC fine-tuning (預計 2-4 週)

### 待處理
- [ ] 收到訓練完成通知後測試 TTS
- [ ] 評估中文發音品質
- [ ] (可選) 處理雲林之聲音檔增加訓練資料
