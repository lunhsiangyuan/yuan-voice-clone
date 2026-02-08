#!/usr/bin/env python3
"""GPT-SoVITS 訓練（跳過預處理，直接訓練 SoVITS + GPT）"""
import os, sys, glob, json, subprocess, time

BASE = "/Users/lunhsiangyuan/Projects/yuan-voice-clone/GPT-SoVITS"
os.chdir(BASE)
sys.path.insert(0, f"{BASE}/GPT_SoVITS")

EXP_NAME = "yuan"
OPT_DIR = f"{BASE}/output/training/{EXP_NAME}"
PRETRAINED = "GPT_SoVITS/pretrained_models"

# 驗證預處理結果
print("=== 檢查預處理資料 ===")
for f in ['2-name2text.txt', '6-name2semantic.tsv']:
    p = os.path.join(OPT_DIR, f)
    assert os.path.exists(p) and os.path.getsize(p) > 10, f"Missing {f}"
    print(f"  OK {f}")
for d in ['3-bert', '4-cnhubert', '5-wav32k']:
    p = os.path.join(OPT_DIR, d)
    c = len(os.listdir(p))
    assert c > 0, f"Empty {d}"
    print(f"  OK {d}/ ({c} files)")

S2G_PATH = f"{PRETRAINED}/gsv-v2final-pretrained/s2G2333k.pth"
S2D_PATH = f"{PRETRAINED}/gsv-v2final-pretrained/s2D2333k.pth"

train_env = {
    **os.environ,
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}",
}

# ========== SoVITS 訓練 ==========
print("\n" + "=" * 60)
print("SoVITS 訓練")
print("=" * 60)

S2_LOG_DIR = f"{OPT_DIR}/logs_s2_v2"
os.makedirs(S2_LOG_DIR, exist_ok=True)
os.makedirs(f'SoVITS_weights/{EXP_NAME}', exist_ok=True)

with open('GPT_SoVITS/configs/s2.json', 'r') as f:
    config = json.load(f)

config['train'].update({
    'epochs': 10, 'batch_size': 4, 'gpu_numbers': '0',
    'save_every_epoch': 5, 'if_save_latest': 1,
    'if_save_every_weights': True,
    'pretrained_s2G': S2G_PATH, 'pretrained_s2D': S2D_PATH,
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
t0 = time.time()
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s2_train.py', '--config', s2_config],
    capture_output=True, text=True, timeout=14400,
    env=train_env, cwd=BASE)

elapsed = time.time() - t0
print(f"耗時: {elapsed/60:.1f} 分鐘")
if result.stdout:
    for line in result.stdout.strip().split('\n')[-30:]:
        print(f"  {line}")
if result.returncode != 0:
    print(f"  SoVITS 訓練失敗 (exit {result.returncode})")
    if result.stderr:
        for line in result.stderr.strip().split('\n')[-20:]:
            print(f"  STDERR: {line}")
    sys.exit(1)

sovits_models = glob.glob(f'SoVITS_weights/{EXP_NAME}/*.pth')
print(f"\nSoVITS 模型: {len(sovits_models)}")
for m in sorted(sovits_models):
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

# ========== GPT 訓練 ==========
print("\n" + "=" * 60)
print("GPT 訓練")
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
t0 = time.time()
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s1_train.py', '--config_file', s1_config],
    env={**train_env, '_CUDA_VISIBLE_DEVICES': ''},
    capture_output=True, text=True, timeout=14400, cwd=BASE)

elapsed = time.time() - t0
print(f"耗時: {elapsed/60:.1f} 分鐘")
if result.stdout:
    for line in result.stdout.strip().split('\n')[-30:]:
        print(f"  {line}")
if result.returncode != 0:
    print(f"  GPT 訓練失敗 (exit {result.returncode})")
    if result.stderr:
        for line in result.stderr.strip().split('\n')[-20:]:
            print(f"  STDERR: {line}")
    sys.exit(1)

gpt_models = glob.glob(f'GPT_weights/{EXP_NAME}/*.ckpt')
print(f"\nGPT 模型: {len(gpt_models)}")
for m in sorted(gpt_models):
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

# 完成
print("\n" + "=" * 60)
print("訓練完成！")
print("=" * 60)
print(f"SoVITS 模型: {len(sovits_models)}")
print(f"GPT 模型: {len(gpt_models)}")
