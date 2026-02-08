# 袁倫祥醫師 GPT-SoVITS 語音克隆訓練 (Kaggle 版)
# 使用前: Settings > Accelerator > GPU T4 x2 > Internet ON
import os, subprocess, sys, glob, json, shutil

WORK = "/kaggle/working"
os.chdir(WORK)

# ========== Step 1: 安裝 GPT-SoVITS ==========
print("=" * 60)
print("Step 1: 安裝 GPT-SoVITS")
print("=" * 60)
os.system("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")

if not os.path.exists(f"{WORK}/GPT-SoVITS/.git"):
    os.system(f"git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git {WORK}/GPT-SoVITS")
os.chdir(f"{WORK}/GPT-SoVITS")

print("安裝 requirements.txt...")
os.system("pip install -q -r requirements.txt")
print("補安裝關鍵套件...")
os.system("pip install -q onnxruntime jieba_fast cn2an pypinyin g2p_en jieba wordsegment "
          "x-transformers rotary-embedding-torch sentencepiece split-lang fast-langdetect "
          "ffmpeg-python PyYAML peft")
os.system("apt-get install -y -qq ffmpeg 2>/dev/null || true")

# 驗證
sys.path.insert(0, f'{WORK}/GPT-SoVITS/GPT_SoVITS')
import importlib
for mod in ['cn2an', 'pypinyin', 'jieba_fast', 'onnxruntime', 'g2p_en', 'x_transformers', 'sentencepiece']:
    try:
        importlib.import_module(mod)
        print(f"  OK: {mod}")
    except ImportError as e:
        print(f"  FAIL: {mod} - {e}")
        os.system(f"pip install -q {mod}")

# ========== Step 2: 下載訓練資料 ==========
print("\n" + "=" * 60)
print("Step 2: 下載訓練資料")
print("=" * 60)
os.makedirs(f"{WORK}/GPT-SoVITS/training_data", exist_ok=True)
DATA_URL = "https://litter.catbox.moe/n1ee8g.zip"
if not os.path.exists(f"{WORK}/GPT-SoVITS/yuan_training_data.zip"):
    print(f"下載: {DATA_URL}")
    os.system(f'wget -q "{DATA_URL}" -O {WORK}/GPT-SoVITS/yuan_training_data.zip')
os.system(f"unzip -o {WORK}/GPT-SoVITS/yuan_training_data.zip -d {WORK}/GPT-SoVITS/training_data/")
wav_count = len(glob.glob(f"{WORK}/GPT-SoVITS/training_data/audio/*.wav"))
print(f"音檔: {wav_count}")

# ========== Step 3: 預訓練模型 ==========
print("\n" + "=" * 60)
print("Step 3: 下載預訓練模型")
print("=" * 60)
os.system("pip install -q huggingface_hub")
os.system(f"huggingface-cli download lj1995/GPT-SoVITS --local-dir GPT_SoVITS/pretrained_models --exclude '*.md' '.gitattributes' 'LICENSE*'")

hubert_dir = "GPT_SoVITS/pretrained_models/chinese-hubert-base"
os.makedirs(hubert_dir, exist_ok=True)
if not (os.path.exists(f"{hubert_dir}/pytorch_model.bin") or os.path.exists(f"{hubert_dir}/model.safetensors")):
    print("下載 HuBERT 權重...")
    os.system(f"wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin -O {hubert_dir}/pytorch_model.bin")
    os.system(f"wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/config.json -O {hubert_dir}/config.json")
    os.system(f"wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/preprocessor_config.json -O {hubert_dir}/preprocessor_config.json")

bert_dir = "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
os.makedirs(bert_dir, exist_ok=True)
if not (os.path.exists(f"{bert_dir}/pytorch_model.bin") or os.path.exists(f"{bert_dir}/model.safetensors")):
    print("下載 BERT 權重...")
    os.system(f"wget -q https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/pytorch_model.bin -O {bert_dir}/pytorch_model.bin")
    os.system(f"wget -q https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/config.json -O {bert_dir}/config.json")

for name, path in [('gsv-v2final-pretrained', 'GPT_SoVITS/pretrained_models/gsv-v2final-pretrained'),
                    ('HuBERT', f'{hubert_dir}/pytorch_model.bin'), ('BERT', f'{bert_dir}/pytorch_model.bin')]:
    exists = os.path.exists(path) or os.path.exists(path.replace('pytorch_model.bin', 'model.safetensors'))
    print(f"  {'OK' if exists else 'FAIL'}: {name}")

# ========== Step 4: 預處理 ==========
print("\n" + "=" * 60)
print("Step 4: 預處理")
print("=" * 60)
EXP_NAME = "yuan"
WAV_DIR = f"{WORK}/GPT-SoVITS/training_data"
OPT_DIR = f"{WORK}/GPT-SoVITS/output/training/{EXP_NAME}"
if os.path.isdir(OPT_DIR):
    shutil.rmtree(OPT_DIR)
os.makedirs(OPT_DIR, exist_ok=True)

orig_list = f"{WORK}/GPT-SoVITS/training_data/transcript_corrected.list"
if not os.path.exists(orig_list):
    lists = glob.glob(f"{WORK}/GPT-SoVITS/training_data/*.list")
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

pretrained_base = "GPT_SoVITS/pretrained_models"
S2G_PATH = next((p for p in [
    f"{pretrained_base}/gsv-v2final-pretrained/s2G2333k.pth",
    f"{pretrained_base}/s2G488k.pth",
] if os.path.exists(p)), None)

env = os.environ.copy()
env.update({
    'inp_text': LIST_FILE, 'inp_wav_dir': '', 'exp_name': EXP_NAME,
    'opt_dir': OPT_DIR, 'is_half': 'True',
    'i_part': '0', 'all_parts': '1', '_CUDA_VISIBLE_DEVICES': '0',
})

def run_step(name, script, extra_env=None, timeout=900):
    print(f"\n--- {name} ---")
    e = env.copy()
    if extra_env:
        e.update(extra_env)
    result = subprocess.run([sys.executable, '-s', script],
        env=e, capture_output=True, text=True, timeout=timeout)
    if result.stdout:
        for line in result.stdout.strip().split('\n')[-10:]:
            print(f"  {line}")
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split('\n')[-10:]:
                print(f"  STDERR: {line}")
        return False
    print(f"  OK")
    return True

ok = run_step("1. 文字/BERT", "GPT_SoVITS/prepare_datasets/1-get-text.py",
    {'bert_pretrained_dir': f'{pretrained_base}/chinese-roberta-wwm-ext-large'})
if ok:
    ok = run_step("2. HuBERT", "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
        {'cnhubert_base_dir': f'{pretrained_base}/chinese-hubert-base', 'sv_path': ''})
if ok and S2G_PATH:
    ok = run_step("3. Semantic", "GPT_SoVITS/prepare_datasets/3-get-semantic.py",
        {'pretrained_s2G': S2G_PATH, 's2config_path': 'GPT_SoVITS/configs/s2.json'})

# 重命名
for src_p, dst_n in [('2-name2text-0.txt', '2-name2text.txt'), ('6-name2semantic-0.tsv', '6-name2semantic.tsv')]:
    src = os.path.join(OPT_DIR, src_p)
    dst = os.path.join(OPT_DIR, dst_n)
    if os.path.exists(src) and not os.path.exists(dst):
        os.rename(src, dst)

print("\n=== 預處理結果 ===")
for f in ['2-name2text.txt', '6-name2semantic.tsv']:
    p = os.path.join(OPT_DIR, f)
    ok_f = os.path.exists(p) and os.path.getsize(p) > 10
    print(f"  {'OK' if ok_f else 'FAIL'} {f}")
for d in ['3-bert', '4-cnhubert', '5-wav32k']:
    p = os.path.join(OPT_DIR, d)
    c = len(os.listdir(p)) if os.path.isdir(p) else 0
    print(f"  {'OK' if c > 0 else 'FAIL'} {d}/ ({c} files)")

# ========== Step 5: SoVITS 訓練 ==========
print("\n" + "=" * 60)
print("Step 5: SoVITS 訓練 (~10 min)")
print("=" * 60)
S2_LOG_DIR = f"{OPT_DIR}/logs_s2_v2"
os.makedirs(S2_LOG_DIR, exist_ok=True)
os.makedirs(f'SoVITS_weights/{EXP_NAME}', exist_ok=True)

S2D_PATH = next((p for p in [
    f"{pretrained_base}/gsv-v2final-pretrained/s2D2333k.pth",
    f"{pretrained_base}/s2D488k.pth",
] if os.path.exists(p)), '')

with open('GPT_SoVITS/configs/s2.json', 'r') as f:
    config = json.load(f)
config['train'].update({
    'epochs': 10, 'batch_size': 16, 'gpu_numbers': '0',
    'save_every_epoch': 2, 'if_save_latest': 1,
    'if_save_every_weights': True,
    'pretrained_s2G': S2G_PATH or '', 'pretrained_s2D': S2D_PATH,
    'half_weights_save_dir': f'SoVITS_weights/{EXP_NAME}',
})
config['data']['exp_dir'] = OPT_DIR
config['model']['version'] = 'v2'
config['s2_ckpt_dir'] = S2_LOG_DIR
config['name'] = EXP_NAME
config['save_weight_dir'] = f'SoVITS_weights/{EXP_NAME}'

s2_config_path = f'{OPT_DIR}/s2_config.json'
with open(s2_config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Config: epochs=10, batch=16, version=v2")
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s2_train.py', '--config', s2_config_path],
    capture_output=True, text=True, timeout=7200)
if result.stdout:
    for line in result.stdout.strip().split('\n')[-20:]:
        print(f"  {line}")
if result.returncode != 0 and result.stderr:
    for line in result.stderr.strip().split('\n')[-15:]:
        print(f"  STDERR: {line}")

sovits_models = glob.glob(f'SoVITS_weights/{EXP_NAME}/*.pth')
print(f"\nSoVITS 模型: {len(sovits_models)}")
for m in sovits_models:
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

# ========== Step 6: GPT 訓練 ==========
print("\n" + "=" * 60)
print("Step 6: GPT 訓練 (~60 min)")
print("=" * 60)
import yaml
S1_LOG_DIR = f"{OPT_DIR}/logs_s1"
os.makedirs(S1_LOG_DIR, exist_ok=True)
os.makedirs(f'GPT_weights/{EXP_NAME}', exist_ok=True)

S1_PATH = ''
for pat in [f"{pretrained_base}/gsv-v2final-pretrained/s1bert25hz*.ckpt", f"{pretrained_base}/s1bert25hz*.ckpt"]:
    matches = glob.glob(pat)
    if matches:
        S1_PATH = matches[0]
        break

SEMANTIC_PATH = f'{OPT_DIR}/6-name2semantic.tsv'
PHONEME_PATH = f'{OPT_DIR}/2-name2text.txt'

yaml_base = next((p for p in ['GPT_SoVITS/configs/s1longer-v2.yaml', 'GPT_SoVITS/configs/s1longer.yaml']
                   if os.path.exists(p)), 'GPT_SoVITS/configs/s1longer.yaml')
with open(yaml_base, 'r') as f:
    gpt_config = yaml.safe_load(f)

gpt_config['train'].update({
    'epochs': 20, 'batch_size': 8, 'save_every_n_epoch': 5,
    'if_save_latest': True, 'if_save_every_weights': True,
    'half_weights_save_dir': f'GPT_weights/{EXP_NAME}', 'exp_name': EXP_NAME,
})
gpt_config['train_semantic_path'] = SEMANTIC_PATH
gpt_config['train_phoneme_path'] = PHONEME_PATH
gpt_config['output_dir'] = S1_LOG_DIR
gpt_config['pretrained_s1'] = S1_PATH

s1_config_path = f'{OPT_DIR}/s1_config.yaml'
with open(s1_config_path, 'w') as f:
    yaml.dump(gpt_config, f)

print(f"Config: epochs=20, batch=8, pretrained={os.path.basename(S1_PATH) if S1_PATH else 'none'}")
gpt_env = os.environ.copy()
gpt_env['_CUDA_VISIBLE_DEVICES'] = '0'
result = subprocess.run(
    [sys.executable, '-s', 'GPT_SoVITS/s1_train.py', '--config_file', s1_config_path],
    env=gpt_env, capture_output=True, text=True, timeout=7200)
if result.stdout:
    for line in result.stdout.strip().split('\n')[-20:]:
        print(f"  {line}")
if result.returncode != 0 and result.stderr:
    for line in result.stderr.strip().split('\n')[-15:]:
        print(f"  STDERR: {line}")

gpt_models = glob.glob(f'GPT_weights/{EXP_NAME}/*.ckpt')
print(f"\nGPT 模型: {len(gpt_models)}")
for m in gpt_models:
    print(f"  {m} ({os.path.getsize(m)/1024/1024:.1f} MB)")

# ========== Step 7: 上傳模型 ==========
print("\n" + "=" * 60)
print("Step 7: 上傳模型")
print("=" * 60)
gpt_models = sorted(glob.glob(f"GPT_weights/{EXP_NAME}/*.ckpt"))
sovits_models = sorted(glob.glob(f"SoVITS_weights/{EXP_NAME}/*.pth"))

if not gpt_models or not sovits_models:
    print("ERROR: 找不到模型!")
    # 列出所有 weights 目錄
    for d in [f'GPT_weights/{EXP_NAME}', f'SoVITS_weights/{EXP_NAME}']:
        if os.path.isdir(d):
            print(f"  {d}: {os.listdir(d)}")
else:
    best_gpt = gpt_models[-1]
    best_sovits = sovits_models[-1]
    print(f"GPT: {best_gpt} ({os.path.getsize(best_gpt)/1024/1024:.1f} MB)")
    print(f"SoVITS: {best_sovits} ({os.path.getsize(best_sovits)/1024/1024:.1f} MB)")

    urls = {}
    for path, label in [(best_sovits, "SOVITS"), (best_gpt, "GPT")]:
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"\n上傳 {label} ({size_mb:.0f} MB)...")
        # 嘗試 catbox (永久)
        r = subprocess.run(
            ["curl", "-F", "reqtype=fileupload", "-F", f"fileToUpload=@{path}",
             "https://catbox.moe/user/api.php"],
            capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and r.stdout.strip().startswith("http"):
            urls[label] = r.stdout.strip()
            print(f"  URL: {urls[label]}")
        else:
            # 備用: litterbox (24h)
            r = subprocess.run(
                ["curl", "-F", "reqtype=fileupload", "-F", "time=24h",
                 "-F", f"fileToUpload=@{path}",
                 "https://litterbox.catbox.moe/resources/internals/api.php"],
                capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and r.stdout.strip().startswith("http"):
                urls[label] = r.stdout.strip()
                print(f"  URL (24h): {urls[label]}")
            else:
                print(f"  上傳失敗: {r.stderr[:200]}")

    print("\n" + "=" * 60)
    print("下載指令 (在本地 Mac 執行):")
    print("=" * 60)
    for label, url in urls.items():
        fname = os.path.basename(best_sovits if label == "SOVITS" else best_gpt)
        print(f"curl -L -o {fname} '{url}'")
    print("=" * 60)

    # 儲存 URLs
    with open(f"{WORK}/download_urls.txt", "w") as f:
        for label, url in urls.items():
            f.write(f"{label}: {url}\n")
    print(f"\nURLs saved to {WORK}/download_urls.txt")

print("\n===== 全部完成! =====")
