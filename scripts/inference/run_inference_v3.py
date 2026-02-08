#!/usr/bin/env python3
"""GPT-SoVITS 推論 v3：修正 ref audio 頭尾靜音 (GitHub #1832 解法)"""
import os, sys, time, requests
import soundfile as sf
import numpy as np

PROJECT = "/Users/lunhsiangyuan/Projects/yuan-voice-clone"
BASE = f"{PROJECT}/GPT-SoVITS"
OUTPUT = f"{PROJECT}/output_greeting_v3.wav"

# 使用 padded reference audio（頭尾各加 0.5s 靜音）
REF_AUDIO = f"{BASE}/training_data/audio/segment_087_padded.wav"
REF_TEXT = "我們稱之為攝護腺的特意性抗原"

GREETING_TEXTS = [
    "各位朋友大家好，我是臺大醫院雲林分院泌尿科的袁倫祥醫師。",
    "非常高興能夠透過這段語音跟大家問好。",
    "今天天氣很好，希望大家都過得開心愉快。",
    "在這裡我想跟大家分享一些泌尿健康的小知識。",
    "首先，定期健康檢查非常重要。",
    "尤其是五十歲以上的男性朋友，建議每年做一次攝護腺的檢查。",
    "包括抽血檢驗攝護腺特異抗原指數。",
    "如果發現異常，千萬不要緊張，及早就醫才是最重要的。",
    "另外，平時也要注意多喝水，保持規律的運動習慣。",
    "這些簡單的生活方式，對於維護泌尿系統的健康都非常有幫助。",
    "如果大家有任何泌尿科相關的問題，歡迎來門診諮詢。",
    "祝大家身體健康，萬事如意。謝謝大家！",
]

PORT = 9881

def synthesize_segment(text, idx):
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": REF_AUDIO,
        "prompt_text": REF_TEXT,
        "prompt_lang": "zh",
        "text_split_method": "cut5",
        "batch_size": 1,
        "media_type": "wav",
        "streaming_mode": False,
        "speed_factor": 0.95,
        "temperature": 0.8,
        "top_p": 0.9,
        "repetition_penalty": 1.35,
    }
    t = time.time()
    r = requests.post(f"http://127.0.0.1:{PORT}/tts", json=payload, timeout=120)
    elapsed = time.time() - t
    if r.status_code != 200:
        print(f"  [{idx+1:2d}/{len(GREETING_TEXTS)}] ERR {r.status_code}: {r.text[:100]}")
        return None
    seg_path = f"/tmp/greeting_v3_seg_{idx:03d}.wav"
    with open(seg_path, 'wb') as f:
        f.write(r.content)
    data, sr = sf.read(seg_path)
    dur = len(data) / sr
    print(f"  [{idx+1:2d}/{len(GREETING_TEXTS)}] OK {elapsed:.1f}s -> {dur:.1f}s: {text[:30]}...")
    return seg_path

def concat_wavs(segments, output):
    all_audio = []
    sr = None
    for seg in segments:
        if seg and os.path.exists(seg):
            data, s = sf.read(seg)
            if sr is None:
                sr = s
            all_audio.append(data)
            all_audio.append(np.zeros(int(sr * 0.35)))
    if all_audio:
        combined = np.concatenate(all_audio)
        sf.write(output, combined, sr)
        duration = len(combined) / sr
        print(f"\n完成: {output}")
        print(f"  時長: {duration:.1f}s ({duration/60:.1f}min)")
        return True
    return False

if __name__ == '__main__':
    print("=" * 60)
    print("GPT-SoVITS v3：ref audio padding 修正 (GitHub #1832)")
    print("=" * 60)
    try:
        requests.get(f"http://127.0.0.1:{PORT}/tts", timeout=3)
    except requests.exceptions.ConnectionError:
        print("ERROR: API 伺服器未啟動！")
        sys.exit(1)
    print(f"\nAPI 就緒，開始合成...\n")
    t0 = time.time()
    segments = []
    for i, text in enumerate(GREETING_TEXTS):
        seg = synthesize_segment(text, i)
        segments.append(seg)
    success = concat_wavs(segments, OUTPUT)
    if success:
        import shutil
        models_dir = f"{PROJECT}/trained_models"
        os.makedirs(models_dir, exist_ok=True)
        shutil.copy2(OUTPUT, f"{models_dir}/greeting_v3.wav")
        print(f"  備份: {models_dir}/greeting_v3.wav")
        print(f"  推理時間: {time.time()-t0:.1f}s")
    print("完成！")
