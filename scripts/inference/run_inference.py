#!/usr/bin/env python3
"""GPT-SoVITS 推論：生成 1 分鐘問候語 (MPS 加速版)"""
import os, sys, time, subprocess, requests, json, signal
import soundfile as sf
import numpy as np

BASE = "/Users/lunhsiangyuan/Projects/yuan-voice-clone/GPT-SoVITS"
PROJECT = "/Users/lunhsiangyuan/Projects/yuan-voice-clone"
OUTPUT = f"{PROJECT}/output_greeting.wav"

# 模型路徑
GPT_MODEL = f"{BASE}/GPT_weights/yuan/yuan-e5.ckpt"
SOVITS_MODEL = f"{BASE}/SoVITS_weights/yuan/yuan_e10_s630.pth"
# 使用 >= 3 秒的 reference audio（GPT-SoVITS 要求 3~10 秒）
REF_AUDIO = f"{BASE}/training_data/audio/segment_087.wav"  # 4.02s
REF_TEXT = "我們稱之為攝護腺的特意性抗原"

# 問候語文本（約 1 分鐘，~250 字）
# 注意：避免混合中英文（如 PSA），會導致 zip file 錯誤
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

def start_api():
    """啟動 API 伺服器（使用 MPS 加速）"""
    import yaml
    config_path = f"{BASE}/GPT_SoVITS/configs/tts_infer.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['custom'] = {
        'bert_base_path': f'{BASE}/GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large',
        'cnhuhbert_base_path': f'{BASE}/GPT_SoVITS/pretrained_models/chinese-hubert-base',
        'device': 'mps',       # MPS 加速（Apple Silicon）
        'is_half': False,       # MPS 不支援 half precision
        't2s_weights_path': GPT_MODEL,
        'version': 'v2',
        'vits_weights_path': SOVITS_MODEL,
    }
    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    print(f"啟動 API 伺服器 (port {PORT}, device=mps)...")
    env = os.environ.copy()
    env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    env['PYTHONPATH'] = f"{BASE}/GPT_SoVITS:{BASE}"

    proc = subprocess.Popen(
        [sys.executable, '-s', f'{BASE}/api_v2.py',
         '-a', '127.0.0.1', '-p', str(PORT),
         '-c', f'{BASE}/GPT_SoVITS/configs/tts_infer.yaml'],
        env=env, cwd=BASE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    return proc

def wait_for_server(timeout=120):
    """等待伺服器啟動"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}/tts", timeout=3)
            return True
        except:
            pass
        time.sleep(2)
        print("  等待伺服器啟動中...")
    return False

def synthesize_segment(text, idx):
    """合成一段語音"""
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

    seg_t = time.time()
    r = requests.post(f"http://127.0.0.1:{PORT}/tts", json=payload, timeout=120)
    elapsed = time.time() - seg_t

    if r.status_code == 200:
        seg_path = f"/tmp/greeting_seg_{idx:03d}.wav"
        with open(seg_path, 'wb') as f:
            f.write(r.content)
        d, s = sf.read(seg_path)
        dur = len(d) / s
        print(f"  [{idx+1:2d}/{len(GREETING_TEXTS)}] OK {elapsed:.1f}s -> {dur:.1f}s: {text[:25]}...")
        return seg_path
    else:
        print(f"  [{idx+1:2d}/{len(GREETING_TEXTS)}] ERR {r.status_code}: {r.text[:100]}")
        return None

def concat_wavs(segments, output):
    """串接所有 wav"""
    all_audio = []
    sr = None
    silence = None

    for seg in segments:
        if seg and os.path.exists(seg):
            data, s = sf.read(seg)
            if sr is None:
                sr = s
                silence = np.zeros(int(sr * 0.3))
            all_audio.append(data)
            all_audio.append(silence)

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
    print("GPT-SoVITS MPS 推理：袁倫祥醫師問候語")
    print("=" * 60)

    proc = start_api()

    try:
        if not wait_for_server():
            print("伺服器啟動失敗！")
            proc.terminate()
            out, _ = proc.communicate(timeout=5)
            print(out[-2000:] if out else "無輸出")
            sys.exit(1)

        print("\n伺服器已就緒 (MPS)，開始合成...\n")
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
            shutil.copy2(OUTPUT, f"{models_dir}/greeting.wav")
            print(f"  備份: {models_dir}/greeting.wav")
            print(f"  推理時間: {time.time()-t0:.1f}s")

    finally:
        print("\n關閉伺服器...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except:
            proc.kill()

    print("完成！")
