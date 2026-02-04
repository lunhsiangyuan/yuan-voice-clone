# Yuan Voice Clone Project

袁倫祥醫師聲音模型訓練專案

## 音檔資料

| 檔案名稱 | 時長 | 用途 |
|---------|------|------|
| 袁倫祥醫師_新雲林之聲_攝護腺常見疾病.mp3 | 39.8 分鐘 | 訓練資料 |
| 袁倫祥醫師_新雲林之聲_1090703_攝護腺疾病.mp3 | 39.8 分鐘 | 訓練資料 |
| 袁倫祥醫師_台灣癌症基金會專訪_攝護腺癌大解惑.mp3 | 17.4 分鐘 | 訓練資料 |

**總訓練時長**: ~97 分鐘

## 聲音模型平台

- **ElevenLabs Professional Voice Clone** (主要)
  - 需要 30+ 分鐘高品質音檔
  - 支援多語言
  - API 可用於 TTS 整合

## 使用方式

```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="your-api-key")
audio = client.text_to_speech.convert(
    voice_id="YOUR_VOICE_ID",
    text="您好，我是袁倫祥醫師。"
)
```

## 授權

本專案音檔僅供個人聲音模型訓練使用。

## Voice Model 資訊

**ElevenLabs Voice ID**: 

### 使用範例

```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="YOUR_API_KEY")

audio = client.text_to_speech.convert(
    voice_id="Z1EU1IiJ7plOOioojpGN",
    text="您好，我是袁倫祥醫師。",
    model_id="eleven_multilingual_v2"
)

with open("output.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)
```

## 目錄結構

```
yuan-voice-clone/
├── README.md
├── .gitignore
├── .env.example
├── voice_id.txt          # Voice ID 配置
├── test_output.mp3       # 測試輸出音檔
├── upload_to_elevenlabs.py
├── chunks/               # 分割後的訓練音檔
│   └── *.mp3
└── 原始音檔/
    ├── 袁倫祥醫師_新雲林之聲_*.mp3
    └── 袁倫祥醫師_台灣癌症基金會專訪_*.mp3
```
