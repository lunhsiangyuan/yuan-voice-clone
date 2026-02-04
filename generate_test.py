from elevenlabs import ElevenLabs
import os

client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

text = "你好，我是袁倫祥醫師。這是一段測試語音，用來確認聲音克隆的效果。如果你聽到這段話，表示設定成功了。"

print("正在生成測試音檔（高穩定度）...")
audio = client.text_to_speech.convert(
    voice_id="6ksMfqyR3w7UcA4bkv1N",
    text=text,
    model_id="eleven_multilingual_v2",
    voice_settings={
        "stability": 0.95,
        "similarity_boost": 0.90,
        "style": 0.0,
        "use_speaker_boost": True
    }
)

with open("test_voice.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("✅ 測試音檔已生成: test_voice.mp3 (高穩定度)")
