# Yuan Voice Clone - 進度記錄

## 目前狀態總覽

```
┌─────────────────────────────────────────────────────────────┐
│                    專案進度儀表板                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ElevenLabs IVC     [##########] 100% ✅ 完成               │
│  ElevenLabs PVC     [######----]  60% ⏳ 待驗證             │
│  GPT-SoVITS 安裝    [##########] 100% ✅ 完成               │
│  GPT-SoVITS 訓練    [----------]   0% 📋 待執行             │
│  聲音分離           [----------]   0% 📋 待執行             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 服務狀態

| 服務 | 狀態 | 端口 | PID |
|------|------|------|-----|
| GPT-SoVITS WebUI | ✅ 運行中 | 9876 | 74458 |
| ElevenLabs API | ✅ 可用 | - | - |

## Session Log

### 2024-02-04 Session 1 (earlier)
- 建立 ElevenLabs IVC 聲音模型
- 測試多種 TTS 參數組合
- 建立 PVC 但驗證失敗 (混音問題)
- 分離台灣癌症基金會音檔
- 建立 Clean PVC (6ksMfqyR3w7UcA4bkv1N)

### 2024-02-04 Session 2 (current)
- ✅ 新增 TTS 方案選擇指南到 README
- ✅ 建立專案規劃文件 (task_plan.md, findings.md, progress.md)
- ✅ GPT-SoVITS 完整安裝
  - Clone repo
  - 建立 Python venv
  - 安裝所有依賴
  - 下載預訓練模型 (~2GB)
  - WebUI 啟動成功 (port 9876)

## Voice IDs

| 平台 | 模型類型 | Voice ID | 狀態 |
|------|---------|----------|------|
| ElevenLabs | IVC | Z1EU1IiJ7plOOioojpGN | ✅ 可用 |
| ElevenLabs | PVC Clean | 6ksMfqyR3w7UcA4bkv1N | ⏳ 待驗證 |

## 檔案結構

```
~/Projects/yuan-voice-clone/
├── README.md              # 專案說明 + TTS 方案指南
├── task_plan.md           # 任務規劃
├── findings.md            # 研究發現
├── progress.md            # 本檔案
├── clean_chunks/          # 乾淨音檔 (6 files)
├── separated/             # 分離結果
│   ├── segments.json
│   └── transcript.txt
├── pvc_clean_voice_id.txt # PVC 配置
└── 原始音檔 (3 files, ~97分鐘)

~/Projects/GPT-SoVITS/
├── venv/                  # Python 虛擬環境
├── GPT_SoVITS/
│   └── pretrained_models/ # 預訓練模型
├── webui.py               # WebUI 入口
└── config.py              # 配置 (port: 9876)
```

## 下一步待辦

1. [ ] 完成 ElevenLabs PVC 聲音驗證
2. [ ] 分離雲林之聲音檔 (pyannote-audio)
3. [ ] 準備 GPT-SoVITS 訓練資料
4. [ ] Google Colab 訓練環境設置
5. [ ] 本地 GPT-SoVITS 推理測試

## 更新時間
最後更新: 2024-02-04 20:40 PST

---

## 2026-02-04 (續)

**20:45** - 新增即時語音通話應用方案
- 使用 BlackHole 虛擬音源線
- 可將 AI 語音即時傳送到 Signal/Discord 通話

---

## TODO List: BlackHole 語音通話設定

### 第一步：安裝軟體
- [ ] 安裝 BlackHole 2ch (`brew install blackhole-2ch`)
- [ ] 安裝 IINA 播放器 (`brew install iina`)
- [ ] 重啟 Mac (如果看不到 BlackHole)

### 第二步：設定多重輸出裝置
- [ ] 打開「音訊 MIDI 設定」(Command + Space 搜尋 MIDI)
- [ ] 點擊左下角「+」→「建立多重輸出裝置」
- [ ] 勾選 BlackHole 2ch + 耳機/揚聲器
- [ ] (選做) 建立「聚集裝置」= 麥克風 + BlackHole

### 第三步：設定播放器
- [ ] 打開 IINA → 偏好設定 → 音訊
- [ ] 音訊裝置選擇「多重輸出裝置」

### 第四步：設定 Discord/Signal
- [ ] Discord: 設定 → 語音與視訊 → 輸入裝置 → BlackHole 2ch
- [ ] Discord: 關閉 Krisp 雜訊抑制、回音消除
- [ ] Signal: 設定 → 通話 → 麥克風 → BlackHole 2ch

### 第五步：測試
- [ ] 用 ElevenLabs 生成測試音檔
- [ ] 找家人/朋友在隔壁房間測試
- [ ] 確認對方能聽到清晰的 AI 聲音

### 進階 (選做)
- [ ] 設定聚集裝置，實現「人聲 + AI 聲」同時輸入
