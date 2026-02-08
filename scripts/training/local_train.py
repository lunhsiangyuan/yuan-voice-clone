#!/usr/bin/env python3
"""袁倫祥醫師 GPT-SoVITS 語音克隆 - 本機 Apple Silicon 訓練"""
import os, sys, glob, json, subprocess, shutil

BASE = "/Users/lunhsiangyuan/Projects/yuan-voice-clone/GPT-SoVITS"
os.chdir(BASE)
sys.path.insert(0, f"{BASE}/GPT_SoVITS")

EXP_NAME = "yuan"
WAV_DIR = f"{BASE}/training_data"
OPT_DIR = f"{BASE}/output/training/{EXP_NAME}"
PRETRAINED = "GPT_SoVITS/pretrained_models"

# Apple Silicon: 使用 MPS
DEVICE = "mps"
IS_HALF = "False"  # MPS 不支援 half precision training

print("=" * 60)
print("Step 1: 驗證環境")
print("=" * 60)
import torch
print(f"PyTorch: {torch.__version__}")
print(f"MPS: {torch.backends.mps.is_available()}")
print(f"Device: {DEVICE}")

# 驗證模型
for name, path in [
    ("gsv-v2final-pretrained", f"{PRETRAINED}/gsv-v2final-pretrained"),
    ("HuBERT", f"{PRETRAINED}/chinese-hubert-base/pytorch_model.bin"),
    ("BERT", f"{PRETRAINED}/chinese-roberta-wwm-ext-large/pytorch_model.bin"),
]:
    exists = os.path.exists(path)
    if exists and os.path.isfile(path):
        size = os.path.getsize(path) / 1024 / 1024
        print(f"  OK: {name} ({size:.0f} MB)")
    elif exists:
        print(f"  OK: {name} (dir)")
    else:
        print(f"  FAIL: {name}")
        sys.exit(1)

wav_count = len(glob.glob(f"{WAV_DIR}/audio/*.wav"))
print(f"音檔: {wav_count}")

# ========== Step 2: 預處理 ==========
print("\n" + "=" * 60)
print("Step 2: 預處理")
print("=" * 60)

if os.path.isdir(OPT_DIR):
    shutil.rmtree(OPT_DIR)
os.makedirs(OPT_DIR, exist_ok=True)

# 標註檔轉絕對路徑
orig_list = f"{WAV_DIR}/transcript_corrected.list"
if not os.path.exists(orig_list):
    lists = glob.glob(f"{WAV_DIR}/*.list")
    orig_list = lists[0] if lists else None
    if not orig_list:
        raise FileNotFoundError("找不到標註檔!")

LIST_FILE = f"{OPT_DIR}/transcript_abs.list"
converted = 0
with open(orig_list, 'r') as fin, open(LIST_FILE, 'w') as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) >= 4:
            wav_abs = os.path.join(WAV_DIR, parts[0])
            if os.path.exists(wav_abs):
                parts[0] = wav_abs
                fout.write('|'.join(parts) + '\n')
                converted += 1
print(f"標註: {converted} 筆")

S2G_PATH = next((p for p in [
    f"{PRETRAINED}/gsv-v2final-pretrained/s2G2333k.pth",
] if os.path.exists(p)), None)

env = os.environ.copy()
env.update({
    'inp_text': LIST_FILE, 'inp_wav_dir': '', 'exp_name': EXP_NAME,
    'opt_dir': OPT_DIR, 'is_half': IS_HALF,
    'i_part': '0', 'all_parts': '1', '_CUDA_VISIBLE_DEVICES': '',
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}:" + env.get('PYTHONPATH', ''),
})

def run_step(name, script, extra_env=None, timeout=1800):
    print(f"\n--- {name} ---")
    e = env.copy()
    if extra_env:
        e.update(extra_env)
    result = subprocess.run([sys.executable, '-s', script],
        env=e, capture_output=True, text=True, timeout=timeout, cwd=BASE)
    if result.stdout:
        for line in result.stdout.strip().split('\n')[-15:]:
            print(f"  {line}")
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split('\n')[-15:]:
                print(f"  STDERR: {line}")
        return False
    print(f"  OK")
    return True

ok = run_step("1. 文字/BERT", "GPT_SoVITS/prepare_datasets/1-get-text.py",
    {'bert_pretrained_dir': f'{PRETRAINED}/chinese-roberta-wwm-ext-large'})

if ok:
    ok = run_step("2. HuBERT", "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
        {'cnhubert_base_dir': f'{PRETRAINED}/chinese-hubert-base', 'sv_path': ''})

if ok and S2G_PATH:
    ok = run_step("3. Semantic", "GPT_SoVITS/prepare_datasets/3-get-semantic.py",
        {'pretrained_s2G': S2G_PATH, 's2config_path': 'GPT_SoVITS/configs/s2.json'})

# 重命名
for src_p, dst_n in [('2-name2text-0.txt', '2-name2text.txt'),
                      ('6-name2semantic-0.tsv', '6-name2semantic.tsv')]:
    src = os.path.join(OPT_DIR, src_p)
    dst = os.path.join(OPT_DIR, dst_n)
    if os.path.exists(src) and not os.path.exists(dst):
        os.rename(src, dst)

print("\n=== 預處理結果 ===")
all_ok = True
for f in ['2-name2text.txt', '6-name2semantic.tsv']:
    p = os.path.join(OPT_DIR, f)
    if os.path.exists(p) and os.path.getsize(p) > 10:
        lc = sum(1 for _ in open(p))
        print(f"  OK {f} ({os.path.getsize(p)} bytes, {lc} lines)")
    else:
        print(f"  FAIL {f}")
        all_ok = False
for d in ['3-bert', '4-cnhubert', '5-wav32k']:
    p = os.path.join(OPT_DIR, d)
    c = len(os.listdir(p)) if os.path.isdir(p) else 0
    print(f"  {'OK' if c > 0 else 'FAIL'} {d}/ ({c} files)")
    if c == 0:
        all_ok = False

if not all_ok:
    print("\n預處理失敗，停止訓練")
    sys.exit(1)

# ========== Step 3: SoVITS 訓練 ==========
print("\n" + "=" * 60)
print("Step 3: SoVITS 訓練")
print("=" * 60)

S2_LOG_DIR = f"{OPT_DIR}/logs_s2_v2"
os.makedirs(S2_LOG_DIR, exist_ok=True)
os.makedirs(f'SoVITS_weights/{EXP_NAME}', exist_ok=True)

S2D_PATH = next((p for p in [
    f"{PRETRAINED}/gsv-v2final-pretrained/s2D2333k.pth",
] if os.path.exists(p)), '')

with open('GPT_SoVITS/configs/s2.json', 'r') as f:
    config = json.load(f)

config['train'].update({
    'epochs': 10, 'batch_size': 4, 'gpu_numbers': '0',
    'save_every_epoch': 5, 'if_save_latest': 1,
    'if_save_every_weights': True,
    'pretrained_s2G': S2G_PATH or '', 'pretrained_s2D': S2D_PATH,
    'half_weights_save_dir': f'SoVITS_weights/{EXP_NAME}',
})
config['data']['exp_dir'] = OPT_DIR
config['model']['version'] = 'v2'
config['s2_ckpt_dir'] = S2_LOG_DIR
config['name'] = EXP_NAME
config['save_weight_dir'] = f'SoVITS_weights/{EXP_NAME}'

s2_config = f'{OPT_DIR}/s2_config.json'
with open(s2_config, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Config: epochs=10, batch=4")
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s2_train.py', '--config', s2_config],
    capture_output=True, text=True, timeout=14400,
    env={**os.environ, 'PYTORCH_ENABLE_MPS_FALLBACK': '1',
         'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}"}, cwd=BASE)
if result.stdout:
    for line in result.stdout.strip().split('\n')[-30:]:
        print(f"  {line}")
if result.returncode != 0 and result.stderr:
    for line in result.stderr.strip().split('\n')[-20:]:
        print(f"  STDERR: {line}")

sovits_models = glob.glob(f'SoVITS_weights/{EXP_NAME}/*.pth')
print(f"\nSoVITS 模型: {len(sovits_models)}")
for m in sovits_models:
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

# ========== Step 4: GPT 訓練 ==========
print("\n" + "=" * 60)
print("Step 4: GPT 訓練")
print("=" * 60)

import yaml

S1_LOG_DIR = f"{OPT_DIR}/logs_s1"
os.makedirs(S1_LOG_DIR, exist_ok=True)
os.makedirs(f'GPT_weights/{EXP_NAME}', exist_ok=True)

S1_PATH = ''
for pat in [f"{PRETRAINED}/gsv-v2final-pretrained/s1bert25hz*.ckpt"]:
    matches = glob.glob(pat)
    if matches:
        S1_PATH = matches[0]
        break

yaml_base = next((p for p in ['GPT_SoVITS/configs/s1longer-v2.yaml',
                                'GPT_SoVITS/configs/s1longer.yaml']
                   if os.path.exists(p)), 'GPT_SoVITS/configs/s1longer.yaml')
with open(yaml_base, 'r') as f:
    gpt_config = yaml.safe_load(f)

gpt_config['train'].update({
    'epochs': 20, 'batch_size': 4, 'save_every_n_epoch': 5,
    'if_save_latest': True, 'if_save_every_weights': True,
    'half_weights_save_dir': f'GPT_weights/{EXP_NAME}', 'exp_name': EXP_NAME,
})
gpt_config['train_semantic_path'] = f'{OPT_DIR}/6-name2semantic.tsv'
gpt_config['train_phoneme_path'] = f'{OPT_DIR}/2-name2text.txt'
gpt_config['output_dir'] = S1_LOG_DIR
gpt_config['pretrained_s1'] = S1_PATH

s1_config = f'{OPT_DIR}/s1_config.yaml'
with open(s1_config, 'w') as f:
    yaml.dump(gpt_config, f)

print(f"Config: epochs=20, batch=4")
gpt_env = {**os.environ, 'PYTORCH_ENABLE_MPS_FALLBACK': '1', '_CUDA_VISIBLE_DEVICES': '',
           'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}"}
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s1_train.py', '--config_file', s1_config],
    env=gpt_env, capture_output=True, text=True, timeout=14400, cwd=BASE)
if result.stdout:
    for line in result.stdout.strip().split('\n')[-30:]:
        print(f"  {line}")
if result.returncode != 0 and result.stderr:
    for line in result.stderr.strip().split('\n')[-20:]:
        print(f"  STDERR: {line}")

gpt_models = glob.glob(f'GPT_weights/{EXP_NAME}/*.ckpt')
print(f"\nGPT 模型: {len(gpt_models)}")
for m in gpt_models:
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

print("\n" + "=" * 60)
print("訓練完成！")
print("=" * 60)
print(f"SoVITS 模型: {len(sovits_models)}")
print(f"GPT 模型: {len(gpt_models)}")
