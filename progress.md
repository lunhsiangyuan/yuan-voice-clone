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
│  訓練資料準備       [##########] 100% ✅ 完成               │
│  Colab 訓練環境     [##########] 100% ✅ 完成               │
│  聲音分離           [----------]   0% 📋 待執行             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Colab 訓練準備

| 項目 | 狀態 | 說明 |
|------|------|------|
| 訓練資料 ZIP | ✅ | yuan_training_data.zip (18MB) |
| 標註文件 | ✅ | 252 片段，已校正 ASR 錯誤 |
| 訓練指南 | ✅ | COLAB_TRAINING.md |
| Colab Notebook | ✅ | colab_training.ipynb |

## 開始訓練

1. 開啟: https://colab.research.google.com/github/RVC-Boss/GPT-SoVITS/blob/main/Colab-WebUI.ipynb
2. 上傳: gpt-sovits-training/yuan_training_data.zip
3. 依照 COLAB_TRAINING.md 步驟操作

## Git Commits

| Commit | 說明 |
|--------|------|
| 5828a37 | Colab 訓練環境設置 |
| ffd6c15 | 訓練資料準備 |
| 1b8d24e | GPT-SoVITS 安裝完成 |
| 47a2bb1 | TTS 方案選擇指南 |

## 更新時間
最後更新: 2024-02-04 22:35 PST

---

## 2026-02-04 (Session 2)

**22:00** - BlackHole 語音通話設定

### 已完成安裝
- [x] BlackHole 2ch (`brew install blackhole-2ch`)
- [x] IINA 播放器 (`brew install iina`)
- [x] Discord (`brew install --cask discord`)
- [x] switchaudio-osx (音訊切換工具)
- [x] Mac Mini 重啟完成

### 已完成設定
- [x] Audio MIDI Setup - 多重輸出裝置
- [x] IINA 音訊輸出設定
- [x] Discord 輸入裝置 → BlackHole 2ch
- [x] ElevenLabs API Key 加入 ~/.zshrc

### 測試音檔已生成
- `test_voice.mp3` - 中文測試 (高穩定度)
- `test_voice_english.mp3` - 英文測試

### 語音參數設定
```
stability: 0.95
similarity_boost: 0.90
style: 0.0
use_speaker_boost: True
```

### 待測試
- [ ] Discord Let's Check 功能驗證
- [ ] 實際 Discord 通話測試
- [ ] Signal 通話測試

---

## 專案完成狀態

### Voice Clone
- ✅ PVC 已建立: `袁倫祥醫師_Clean`
- ✅ Voice ID: `6ksMfqyR3w7UcA4bkv1N`
- ✅ API Key 已設定

### BlackHole 語音路由
- ✅ 軟體安裝完成
- ✅ 音訊路由設定完成
- ⏳ 待實際通話測試

---

## 2026-02-08

### Git 整理
- [x] 更新 .gitignore（排除 GPT-SoVITS/、models/、*.wav、*.ckpt 等）
- [x] 腳本重新組織至 scripts/{inference,training,setup}/
- [x] git filter-repo 清理 wav 歷史（.git 36MB → 18MB）
- [x] Force push 到 GitHub

### Kaggle 訓練模型
- [x] GPT yuan-e20.ckpt (20 epochs, Kaggle T4 GPU) — 已下載至 models/
- [x] SoVITS yuan_e10_s630.pth (10 epochs) — 音色正常
- [x] API 已切換至 e20 模型（tts_infer.yaml）

### 語音合成測試
- [x] 新年問好音檔（GPT-SoVITS, e5）
- [x] 衛教音檔（ElevenLabs + GPT-SoVITS 對比）
- [x] e20 模型衛教測試

### 已知問題 — 尾音截斷 (Tail Truncation)
**狀態**: 🔴 未解決

**症狀**: 每句話最後一個字的能量急速衰減，聽起來被切成一半

**根因**: T2S (GPT) 模型 EOS token 偵測不穩定，導致最後幾個 semantic token 品質下降。這是 GPT-SoVITS 架構性問題，e5/e20 都存在。

**已嘗試的方法**:
| 方法 | 結果 |
|------|------|
| 短填充詞「嗯。」 | 部分改善，但不穩定 |
| 長犧牲句 + cut5 分割 | e20 模型下產生重複 |
| 無修剪直接輸出 | 尾音仍然衰減 |
| 「嗯好。」+ 回切 450ms | 切得不精確，仍有截斷 |

**下一步 TODO**:
- [ ] 嘗試更長的填充句（如「，好的，謝謝大家。」）+ 動態切割
- [ ] 嘗試 GPT-SoVITS v3/v4 模型架構（可能已修復此問題）
- [ ] 嘗試不同 reference audio 看是否影響 EOS 行為
- [ ] 研究 GPT-SoVITS GitHub Issues 是否有官方修復
- [ ] 考慮只重訓 GPT 更多 epochs（30-50）看是否改善
- [ ] 考慮混合方案：GPT-SoVITS 出稿 + 手動後製尾音

### 模型設定（目前生效）
```yaml
# tts_infer.yaml (GPT-SoVITS/GPT_SoVITS/configs/)
t2s_weights_path: GPT_weights/yuan/yuan-e20.ckpt  # Kaggle 20 epochs
vits_weights_path: SoVITS_weights/yuan/yuan_e10_s630.pth
device: mps
version: v2
```
