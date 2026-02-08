#!/usr/bin/env python3
"""GPT-SoVITS GPT (s1) 訓練"""
import os, sys, glob, json, time

BASE = "/Users/lunhsiangyuan/Projects/yuan-voice-clone/GPT-SoVITS"
os.chdir(BASE)

EXP_NAME = "yuan"
OPT_DIR = f"{BASE}/output/training/{EXP_NAME}"
PRETRAINED = "GPT_SoVITS/pretrained_models"

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

print(f"Pretrained GPT: {S1_PATH}")

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
print("Starting GPT training...")

import subprocess
t0 = time.time()
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s1_train.py', '--config_file', s1_config],
    env={**os.environ, 'PYTORCH_ENABLE_MPS_FALLBACK': '1', '_CUDA_VISIBLE_DEVICES': '',
         'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}"},
    capture_output=True, text=True, timeout=14400, cwd=BASE)

elapsed = time.time() - t0
print(f"\n耗時: {elapsed/60:.1f} 分鐘")
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
print("\nGPT 訓練完成！")
