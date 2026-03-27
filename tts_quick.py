#!/usr/bin/env python3
"""
Voice Clone TTS — 語言自動路由
  中文 → GPT-SoVITS v4 LoRA (本地)
  英文 → ElevenLabs PVC (雲端)

Usage:
    python tts_quick.py "中文文字"                    # 自動偵測 → GPT-SoVITS
    python tts_quick.py "English text"                # 自動偵測 → ElevenLabs
    python tts_quick.py "文字" --lang zh              # 強制中文
    python tts_quick.py "text" --lang en              # 強制英文
    python tts_quick.py --file input.txt -o out.wav

需先啟動 GPT-SoVITS API server (中文用):
    cd ~/Projects/yuan-voice-clone/GPT-SoVITS
    source ../.venv/bin/activate
    python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
"""

import argparse
import requests
import sys
import os
import re
from datetime import datetime

# === GPT-SoVITS (中文) ===
SOVITS_API = "http://127.0.0.1:9880"
SOVITS_REF = os.path.expanduser(
    "~/Projects/yuan-voice-clone/GPT-SoVITS/training_data/audio/segment_213.wav"
)
SOVITS_REF_TEXT = "但是前提就是病患得配合醫師的追蹤的這個頻率這樣"
SOVITS_BASE = os.path.expanduser("~/Projects/yuan-voice-clone/GPT-SoVITS")
SOVITS_MODELS = {
    "v4": {
        "gpt": "GPT_weights/yuan_v4_r2/yuan_v4_r2-e20.ckpt",
        "sovits": "SoVITS_weights/v4_r2/yuan_e20_s940_l32.pth",
    },
    "v2": {
        "gpt": "GPT_weights/yuan/yuan-e20.ckpt",
        "sovits": "SoVITS_weights/yuan/yuan_e10_s630.pth",
    },
}

# === ElevenLabs (英文) ===
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "j2yC6F19C8AnpqFtdF4O"
ELEVENLABS_MODEL = "eleven_multilingual_v2"


def detect_lang(text):
    """Simple language detection: if >30% CJK chars → zh, else en"""
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    return "zh" if cjk / max(len(text), 1) > 0.3 else "en"


def tts_sovits(text, output_path, speed=1.0):
    """Generate with GPT-SoVITS (local)"""
    try:
        requests.get(f"{SOVITS_API}/tts", timeout=3)
    except requests.ConnectionError:
        print("GPT-SoVITS API 未啟動！")
        return False

    m = SOVITS_MODELS["v4"]
    gpt = os.path.join(SOVITS_BASE, m["gpt"])
    sovits = os.path.join(SOVITS_BASE, m["sovits"])
    requests.get(f"{SOVITS_API}/set_gpt_weights", params={"weights_path": gpt})
    requests.get(f"{SOVITS_API}/set_sovits_weights", params={"weights_path": sovits})

    r = requests.post(f"{SOVITS_API}/tts", json={
        "text": text, "text_lang": "zh",
        "ref_audio_path": SOVITS_REF, "prompt_text": SOVITS_REF_TEXT, "prompt_lang": "zh",
        "text_split_method": "cut0", "batch_size": 1,
        "media_type": "wav", "streaming_mode": False, "speed_factor": speed,
    }, timeout=300)

    if r.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(r.content)
        print(f"[GPT-SoVITS] {output_path} ({len(r.content)/1024:.0f}KB)")
        return True
    print(f"[GPT-SoVITS] 失敗: {r.status_code}")
    return False


def tts_elevenlabs(text, output_path):
    """Generate with ElevenLabs (cloud)"""
    if not ELEVENLABS_API_KEY:
        print("ELEVENLABS_API_KEY 未設定！請在 ~/.zshrc 設定或 export ELEVENLABS_API_KEY=...")
        return False

    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {"stability": 0.85, "similarity_boost": 0.90},
        },
        timeout=60,
    )

    if r.status_code == 200:
        # ElevenLabs returns mp3, convert to wav if needed
        mp3_path = output_path.replace(".wav", ".mp3")
        with open(mp3_path, "wb") as f:
            f.write(r.content)
        if output_path.endswith(".wav"):
            os.system(f'ffmpeg -i "{mp3_path}" "{output_path}" -y -loglevel quiet')
            os.remove(mp3_path)
        print(f"[ElevenLabs] {output_path} ({os.path.getsize(output_path)/1024:.0f}KB)")
        return True
    print(f"[ElevenLabs] 失敗: {r.status_code} - {r.text[:200]}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Voice Clone TTS — 語言自動路由")
    parser.add_argument("text", nargs="?", help="要合成的文字")
    parser.add_argument("--file", "-f", help="從文字檔讀取")
    parser.add_argument("--output", "-o", help="輸出檔案路徑")
    parser.add_argument("--lang", "-l", choices=["zh", "en", "auto"], default="auto",
                        help="語言 (auto=自動偵測)")
    parser.add_argument("--speed", "-s", type=float, default=1.0, help="語速 (僅中文)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r") as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        print("請提供文字或 --file")
        sys.exit(1)

    lang = args.lang if args.lang != "auto" else detect_lang(text)
    print(f"語言: {lang} | 引擎: {'GPT-SoVITS' if lang == 'zh' else 'ElevenLabs'}")

    if args.output:
        output = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = os.path.expanduser(f"~/Projects/yuan-voice-clone/output_{lang}_{ts}.wav")

    import time
    t0 = time.time()

    if lang == "zh":
        ok = tts_sovits(text, output, speed=args.speed)
    else:
        ok = tts_elevenlabs(text, output)

    if ok:
        print(f"耗時: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
