#!/usr/bin/env python3
"""GPT 續訓：從 epoch 5 繼續到 epoch 15，低資源模式"""
import os, sys, glob, yaml, subprocess, time

BASE = "/Users/lunhsiangyuan/Projects/yuan-voice-clone/GPT-SoVITS"
os.chdir(BASE)

EXP_NAME = "yuan"
OPT_DIR = f"{BASE}/output/training/{EXP_NAME}"
S1_LOG_DIR = f"{OPT_DIR}/logs_s1"

# 找到 resume checkpoint
RESUME_CKPT = f"{S1_LOG_DIR}/ckpt/epoch=4-step=75.ckpt"
assert os.path.exists(RESUME_CKPT), f"Checkpoint not found: {RESUME_CKPT}"

yaml_base = next((p for p in ['GPT_SoVITS/configs/s1longer-v2.yaml',
                                'GPT_SoVITS/configs/s1longer.yaml']
                   if os.path.exists(p)), 'GPT_SoVITS/configs/s1longer.yaml')
with open(yaml_base, 'r') as f:
    gpt_config = yaml.safe_load(f)

gpt_config['train'].update({
    'epochs': 15,
    'batch_size': 2,            # 降低 batch size (原本 4)
    'save_every_n_epoch': 5,
    'if_save_latest': True,
    'if_save_every_weights': True,
    'half_weights_save_dir': f'GPT_weights/{EXP_NAME}',
    'exp_name': EXP_NAME,
    'num_workers': 1,           # 降低 worker 數
})
gpt_config['train_semantic_path'] = f'{OPT_DIR}/6-name2semantic.tsv'
gpt_config['train_phoneme_path'] = f'{OPT_DIR}/2-name2text.txt'
gpt_config['output_dir'] = S1_LOG_DIR
gpt_config['pretrained_s1'] = ''  # 不用 pretrained，從 checkpoint 續訓

s1_config = f'{OPT_DIR}/s1_config_resume.yaml'
with open(s1_config, 'w') as f:
    yaml.dump(gpt_config, f)

print(f"GPT 續訓：epoch 5 -> 15, batch=2, workers=1")
print(f"Resume from: {RESUME_CKPT}")
print(f"Config: {s1_config}")
print(f"開始時間: {time.strftime('%H:%M:%S')}")
print("=" * 50)

t0 = time.time()
env = {
    **os.environ,
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    '_CUDA_VISIBLE_DEVICES': '',
    'PYTHONPATH': f"{BASE}/GPT_SoVITS:{BASE}",
    'OMP_NUM_THREADS': '2',         # 限制 CPU 線程
    'MKL_NUM_THREADS': '2',
}

with open('/tmp/gpt_resume_train.log', 'w') as logf:
    proc = subprocess.Popen(
        [sys.executable, '-u', '-s', 'GPT_SoVITS/s1_train.py',
         '--config_file', s1_config],
        env=env, cwd=BASE,
        stdout=logf, stderr=subprocess.STDOUT,
    )
    print(f"PID: {proc.pid}")
    proc.wait()

elapsed = time.time() - t0
print(f"\n完成！耗時: {elapsed/60:.1f} 分鐘 ({elapsed/3600:.1f} 小時)")

gpt_models = sorted(glob.glob(f'GPT_weights/{EXP_NAME}/*.ckpt'))
print(f"GPT 模型: {len(gpt_models)}")
for m in gpt_models:
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")
