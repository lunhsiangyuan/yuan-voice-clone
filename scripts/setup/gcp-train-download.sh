#!/bin/bash
# ============================================================
# GPT-SoVITS 全自動訓練 + 下載腳本
# GCP L4 GPU Spot VM — 一鍵完成
# ============================================================
#
# 流程: 建立 VM → 安裝環境 → 訓練 → 下載模型 → 關機
# 費用: ~$0.40 USD (Spot VM ~$0.25/hr × ~1.5hr)
#
# 使用方式:
#   bash gcp-train-download.sh
# ============================================================

set -euo pipefail

# === 配置 ===
INSTANCE_NAME="gpt-sovits-trainer"
ZONE="asia-east1-c"
MACHINE_TYPE="g2-standard-4"   # 1x L4 GPU, 4 vCPU, 16GB RAM
BOOT_DISK_SIZE="150"
IMAGE_PROJECT="deeplearning-platform-release"
YUAN_PROJECT="$HOME/Projects/yuan-voice-clone"
MODEL_OUTPUT_DIR="$YUAN_PROJECT/trained_models"

# === Pre-flight ===
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
    echo "ERROR: 未設定 GCP project"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# 偵測 Deep Learning VM image
echo "偵測最新 Deep Learning VM image..."
IMAGE_FAMILY=$(gcloud compute images list \
    --project="$IMAGE_PROJECT" \
    --filter="family:pytorch AND family:cu" \
    --format="value(family)" \
    --sort-by="~creationTimestamp" 2>/dev/null | head -1)

if [ -z "$IMAGE_FAMILY" ]; then
    IMAGE_FAMILY=$(gcloud compute images list \
        --project="$IMAGE_PROJECT" \
        --filter="family:pytorch" \
        --format="value(family)" \
        --sort-by="~creationTimestamp" 2>/dev/null | head -1)
fi

if [ -z "$IMAGE_FAMILY" ]; then
    echo "ERROR: 無法偵測 PyTorch image family"
    exit 1
fi

echo ""
echo "=== GPT-SoVITS 全自動訓練 ==="
echo "Project:  $PROJECT"
echo "Instance: $INSTANCE_NAME"
echo "Zone:     $ZONE"
echo "Machine:  $MACHINE_TYPE (1x NVIDIA L4, 24GB VRAM)"
echo "Image:    $IMAGE_FAMILY"
echo "Disk:     ${BOOT_DISK_SIZE}GB SSD"
echo "Type:     Spot VM (~\$0.25/hr)"
echo ""
echo "預估流程:"
echo "  安裝環境: ~15 min"
echo "  預處理:   ~10 min"
echo "  SoVITS:   ~10 min"
echo "  GPT:      ~60 min"
echo "  總計:     ~95 min (~\$0.40)"
echo ""
read -p "確認開始？(y/N) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# === 檢查是否已有 VM ===
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" &>/dev/null; then
    echo "VM '$INSTANCE_NAME' 已存在"
    STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="value(status)")
    if [ "$STATUS" = "TERMINATED" ] || [ "$STATUS" = "STOPPED" ]; then
        echo "VM 狀態: $STATUS，正在啟動..."
        gcloud compute instances start "$INSTANCE_NAME" --zone="$ZONE"
    elif [ "$STATUS" = "RUNNING" ]; then
        echo "VM 已在運行"
    fi
else
    # === 建立 Spot VM ===
    echo ""
    echo "[1/6] 建立 GCP Spot VM..."
    gcloud compute instances create "$INSTANCE_NAME" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --boot-disk-size="${BOOT_DISK_SIZE}GB" \
        --boot-disk-type=pd-ssd \
        --image-family="$IMAGE_FAMILY" \
        --image-project="$IMAGE_PROJECT" \
        --maintenance-policy=TERMINATE \
        --provisioning-model=SPOT \
        --instance-termination-action=STOP \
        --metadata="install-nvidia-driver=True" \
        --scopes=default,storage-ro \
        --tags=gpu-instance
    echo "VM 建立成功"
fi

# === 等待 SSH ===
echo ""
echo "[2/6] 等待 SSH 就緒..."
sleep 20
for i in $(seq 1 20); do
    if gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="echo ready" 2>/dev/null; then
        echo "SSH 連線成功!"
        break
    fi
    echo "  等待 SSH... ($i/20)"
    sleep 15
done

if ! gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="echo ready" 2>/dev/null; then
    echo "ERROR: SSH 連線逾時"
    exit 1
fi

# === 上傳訓練資料 ===
echo ""
echo "[3/6] 上傳訓練資料..."

# 檢查訓練資料
if [ ! -f "$YUAN_PROJECT/gpt-sovits-training/yuan_training_data.zip" ]; then
    echo "ERROR: 找不到 $YUAN_PROJECT/gpt-sovits-training/yuan_training_data.zip"
    echo "請先準備訓練資料"
    exit 1
fi

gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="mkdir -p ~/training_data"
gcloud compute scp "$YUAN_PROJECT/gpt-sovits-training/yuan_training_data.zip" \
    "$INSTANCE_NAME":~/training_data/ --zone="$ZONE"

# 上傳標註文件
for f in "$YUAN_PROJECT/gpt-sovits-training"/*.list; do
    if [ -f "$f" ]; then
        gcloud compute scp "$f" "$INSTANCE_NAME":~/training_data/ --zone="$ZONE"
    fi
done

echo "訓練資料上傳完成"

# === 上傳並執行訓練腳本 ===
echo ""
echo "[4/6] 開始安裝環境 + 訓練 (在 tmux 中背景執行)..."

TRAIN_SCRIPT=$(mktemp)
cat > "$TRAIN_SCRIPT" << 'TRAIN_EOF'
#!/bin/bash
set -eo pipefail

LOG="/tmp/gpt-sovits-train.log"
exec > >(tee -a "$LOG") 2>&1

EXP_NAME="yuan"
WORKDIR="$HOME/GPT-SoVITS"

echo "=== GPT-SoVITS 訓練開始 $(date) ==="

# ============================================================
# Step 1: 等待 GPU
# ============================================================
echo "[1/7] 等待 NVIDIA 驅動..."
for i in $(seq 1 30); do
    if nvidia-smi &>/dev/null; then
        echo "GPU 就緒!"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
        break
    fi
    echo "  等待... ($i/30)"
    sleep 10
done
if ! nvidia-smi &>/dev/null; then
    echo "ERROR: NVIDIA 驅動安裝失敗"
    exit 1
fi

# ============================================================
# Step 2: 安裝依賴
# ============================================================
echo "[2/7] 安裝系統依賴..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg libsndfile1

echo "Clone GPT-SoVITS..."
cd ~
if [ ! -d "GPT-SoVITS" ]; then
    git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git
fi
cd "$WORKDIR"

echo "設定 Python 環境..."
if command -v conda &>/dev/null; then
    eval "$(conda shell.bash hook)"
    conda create -n gptsovits python=3.10 -y 2>/dev/null || true
    conda activate gptsovits
fi

pip install --upgrade pip -q
pip install -r requirements.txt -q 2>&1 | tail -5
pip install onnxruntime jieba_fast cn2an pypinyin g2p_en jieba wordsegment \
    x-transformers rotary-embedding-torch sentencepiece split-lang fast-langdetect \
    ffmpeg-python PyYAML peft huggingface_hub -q 2>&1 | tail -5

echo "驗證關鍵套件..."
python3 -c "import cn2an, pypinyin, onnxruntime, g2p_en, sentencepiece; print('OK')"

# ============================================================
# Step 3: 下載預訓練模型
# ============================================================
echo "[3/7] 下載預訓練模型..."
huggingface-cli download lj1995/GPT-SoVITS \
    --local-dir GPT_SoVITS/pretrained_models \
    --exclude '*.md' '.gitattributes' 'LICENSE*' 2>&1 | tail -5

# HuBERT 權重
HUBERT_DIR="GPT_SoVITS/pretrained_models/chinese-hubert-base"
mkdir -p "$HUBERT_DIR"
if [ ! -f "$HUBERT_DIR/pytorch_model.bin" ] && [ ! -f "$HUBERT_DIR/model.safetensors" ]; then
    echo "下載 HuBERT 權重..."
    wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin -O "$HUBERT_DIR/pytorch_model.bin"
    wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/config.json -O "$HUBERT_DIR/config.json"
    wget -q https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/preprocessor_config.json -O "$HUBERT_DIR/preprocessor_config.json"
fi

# BERT 權重
BERT_DIR="GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
mkdir -p "$BERT_DIR"
if [ ! -f "$BERT_DIR/pytorch_model.bin" ] && [ ! -f "$BERT_DIR/model.safetensors" ]; then
    echo "下載 BERT 權重..."
    wget -q https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/pytorch_model.bin -O "$BERT_DIR/pytorch_model.bin"
    wget -q https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/config.json -O "$BERT_DIR/config.json"
fi

# ============================================================
# Step 4: 準備訓練資料
# ============================================================
echo "[4/7] 準備訓練資料..."
mkdir -p training_data
cd "$WORKDIR"

# 解壓縮訓練資料
if [ -f ~/training_data/yuan_training_data.zip ]; then
    unzip -o ~/training_data/yuan_training_data.zip -d training_data/ | tail -3
fi

# 複製標註文件
for f in ~/training_data/*.list; do
    [ -f "$f" ] && cp "$f" training_data/
done

WAV_COUNT=$(find training_data/audio -name "*.wav" 2>/dev/null | wc -l)
echo "音檔數量: $WAV_COUNT"

# ============================================================
# Step 5: 預處理
# ============================================================
echo "[5/7] 預處理..."

OPT_DIR="output/training/$EXP_NAME"
rm -rf "$OPT_DIR"
mkdir -p "$OPT_DIR"

PRETRAINED="GPT_SoVITS/pretrained_models"
WAV_DIR="$WORKDIR/training_data"

# 標註檔轉絕對路徑
python3 << PYEOF
import os, glob
wav_dir = "$WAV_DIR"
opt_dir = "$OPT_DIR"
orig = glob.glob(f"{wav_dir}/*.list")
if not orig:
    print("ERROR: 找不到標註檔")
    exit(1)
orig = orig[0]
out_path = f"{opt_dir}/transcript_abs.list"
count = 0
with open(orig) as fin, open(out_path, 'w') as fout:
    for line in fin:
        line = line.strip()
        if not line: continue
        parts = line.split('|')
        if len(parts) >= 4:
            wav_abs = os.path.join(wav_dir, parts[0])
            if os.path.exists(wav_abs):
                parts[0] = wav_abs
                fout.write('|'.join(parts) + '\n')
                count += 1
print(f"標註檔: {count} 筆")
PYEOF

# 預處理步驟
export inp_text="$OPT_DIR/transcript_abs.list"
export inp_wav_dir=""
export exp_name="$EXP_NAME"
export opt_dir="$OPT_DIR"
export is_half="True"
export i_part="0"
export all_parts="1"
export _CUDA_VISIBLE_DEVICES="0"

echo "  [5a] 文字/BERT..."
export bert_pretrained_dir="$PRETRAINED/chinese-roberta-wwm-ext-large"
python3 -s GPT_SoVITS/prepare_datasets/1-get-text.py 2>&1 | tail -5

echo "  [5b] HuBERT..."
export cnhubert_base_dir="$PRETRAINED/chinese-hubert-base"
export sv_path=""
python3 -s GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py 2>&1 | tail -5

S2G_PATH=$(find "$PRETRAINED" -name "s2G*.pth" | head -1)
if [ -n "$S2G_PATH" ]; then
    echo "  [5c] Semantic..."
    export pretrained_s2G="$S2G_PATH"
    export s2config_path="GPT_SoVITS/configs/s2.json"
    python3 -s GPT_SoVITS/prepare_datasets/3-get-semantic.py 2>&1 | tail -5
fi

# 重命名移除 -0 後綴
for pair in "2-name2text-0.txt:2-name2text.txt" "6-name2semantic-0.tsv:6-name2semantic.tsv"; do
    src="$OPT_DIR/${pair%%:*}"
    dst="$OPT_DIR/${pair##*:}"
    [ -f "$src" ] && [ ! -f "$dst" ] && mv "$src" "$dst"
done

echo "  預處理結果:"
for f in 2-name2text.txt 6-name2semantic.tsv; do
    if [ -f "$OPT_DIR/$f" ] && [ -s "$OPT_DIR/$f" ]; then
        echo "    OK: $f ($(wc -l < "$OPT_DIR/$f") lines)"
    else
        echo "    FAIL: $f"
    fi
done

# ============================================================
# Step 6a: 訓練 SoVITS
# ============================================================
echo "[6/7] 訓練 SoVITS (~10 min)..."

mkdir -p "SoVITS_weights/$EXP_NAME"

python3 << PYEOF
import json, glob, os
opt_dir = "$OPT_DIR"
exp_name = "$EXP_NAME"
pretrained = "$PRETRAINED"

with open('GPT_SoVITS/configs/s2.json') as f:
    config = json.load(f)

s2g = next((p for p in [f"{pretrained}/gsv-v2final-pretrained/s2G2333k.pth", f"{pretrained}/s2G488k.pth"] if os.path.exists(p)), '')
s2d = next((p for p in [f"{pretrained}/gsv-v2final-pretrained/s2D2333k.pth", f"{pretrained}/s2D488k.pth"] if os.path.exists(p)), '')

config['train'].update({
    'epochs': 10, 'batch_size': 16, 'gpu_numbers': '0',
    'save_every_epoch': 2, 'if_save_latest': 1, 'if_save_every_weights': True,
    'pretrained_s2G': s2g, 'pretrained_s2D': s2d,
    'half_weights_save_dir': f'SoVITS_weights/{exp_name}'
})
config['data']['exp_dir'] = opt_dir
config['model']['version'] = 'v2'
config['s2_ckpt_dir'] = f'{opt_dir}/logs_s2_v2'
config['name'] = exp_name
config['save_weight_dir'] = f'SoVITS_weights/{exp_name}'

os.makedirs(f'{opt_dir}/logs_s2_v2', exist_ok=True)
with open(f'{opt_dir}/s2_config.json', 'w') as f:
    json.dump(config, f, indent=2)
print(f"SoVITS config: epochs=10, batch=16")
PYEOF

python3 -s GPT_SoVITS/s2_train.py --config "$OPT_DIR/s2_config.json" 2>&1 | tail -20
echo "SoVITS 模型:"
ls -lh "SoVITS_weights/$EXP_NAME/"*.pth 2>/dev/null || echo "  (none)"

# ============================================================
# Step 6b: 訓練 GPT
# ============================================================
echo "[7/7] 訓練 GPT (~60 min)..."

mkdir -p "GPT_weights/$EXP_NAME"

python3 << PYEOF
import yaml, glob, os
opt_dir = "$OPT_DIR"
exp_name = "$EXP_NAME"
pretrained = "$PRETRAINED"

yaml_base = next((p for p in ['GPT_SoVITS/configs/s1longer-v2.yaml', 'GPT_SoVITS/configs/s1longer.yaml'] if os.path.exists(p)))
with open(yaml_base) as f:
    config = yaml.safe_load(f)

s1 = next((m for pat in [f"{pretrained}/gsv-v2final-pretrained/s1bert25hz*.ckpt", f"{pretrained}/s1bert25hz*.ckpt"] for m in glob.glob(pat)), '')

config['train'].update({
    'epochs': 20, 'batch_size': 8, 'save_every_n_epoch': 5,
    'if_save_latest': True, 'if_save_every_weights': True,
    'half_weights_save_dir': f'GPT_weights/{exp_name}',
    'exp_name': exp_name
})
config['train_semantic_path'] = f'{opt_dir}/6-name2semantic.tsv'
config['train_phoneme_path'] = f'{opt_dir}/2-name2text.txt'
config['output_dir'] = f'{opt_dir}/logs_s1'
config['pretrained_s1'] = s1

os.makedirs(f'{opt_dir}/logs_s1', exist_ok=True)
with open(f'{opt_dir}/s1_config.yaml', 'w') as f:
    yaml.dump(config, f)
print(f"GPT config: epochs=20, batch=8")
PYEOF

python3 -s GPT_SoVITS/s1_train.py --config_file "$OPT_DIR/s1_config.yaml" 2>&1 | tail -20
echo "GPT 模型:"
ls -lh "GPT_weights/$EXP_NAME/"*.ckpt 2>/dev/null || echo "  (none)"

# ============================================================
# 完成！
# ============================================================
echo ""
echo "========================================="
echo "  訓練完成! $(date)"
echo "========================================="
echo "  SoVITS: $(ls SoVITS_weights/$EXP_NAME/*.pth 2>/dev/null | wc -l) models"
echo "  GPT:    $(ls GPT_weights/$EXP_NAME/*.ckpt 2>/dev/null | wc -l) models"
echo "========================================="

# 標記完成
echo "DONE" > /tmp/training-done
TRAIN_EOF

# 上傳訓練腳本
gcloud compute scp "$TRAIN_SCRIPT" "$INSTANCE_NAME":/tmp/train-gptsovits.sh --zone="$ZONE"
rm -f "$TRAIN_SCRIPT"

# 在 tmux 中執行
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="
    chmod +x /tmp/train-gptsovits.sh
    tmux new-session -d -s train 'bash /tmp/train-gptsovits.sh; echo DONE > /tmp/training-done'
"

echo ""
echo "訓練已在背景執行 (tmux session: train)"
echo "  監控: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- 'tmux attach -t train'"
echo "  日誌: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- 'tail -30 /tmp/gpt-sovits-train.log'"
echo ""

# === 等待訓練完成 ===
echo "[5/6] 等待訓練完成 (預估 ~90 min)..."
echo "  (可以 Ctrl+C 中斷等待，稍後手動下載)"
echo ""

STARTED=$(date +%s)
while true; do
    if gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="test -f /tmp/training-done" 2>/dev/null; then
        echo ""
        echo "訓練完成!"
        break
    fi

    ELAPSED=$(( ($(date +%s) - STARTED) / 60 ))
    PROGRESS=$(gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" \
        --command="tail -1 /tmp/gpt-sovits-train.log 2>/dev/null" 2>/dev/null || echo "等待中...")
    echo "  [${ELAPSED}m] $PROGRESS"

    sleep 60
done

# === 下載模型 ===
echo ""
echo "[6/6] 下載訓練模型到本地..."
mkdir -p "$MODEL_OUTPUT_DIR"

# 下載所有模型
gcloud compute scp --recurse \
    "$INSTANCE_NAME":~/GPT-SoVITS/GPT_weights/yuan/ \
    "$MODEL_OUTPUT_DIR/GPT_weights_yuan/" --zone="$ZONE" 2>/dev/null || true

gcloud compute scp --recurse \
    "$INSTANCE_NAME":~/GPT-SoVITS/SoVITS_weights/yuan/ \
    "$MODEL_OUTPUT_DIR/SoVITS_weights_yuan/" --zone="$ZONE" 2>/dev/null || true

echo ""
echo "============================================================"
echo "  下載完成!"
echo "============================================================"
echo ""
echo "  模型位置: $MODEL_OUTPUT_DIR"
ls -lh "$MODEL_OUTPUT_DIR"/GPT_weights_yuan/*.ckpt 2>/dev/null
ls -lh "$MODEL_OUTPUT_DIR"/SoVITS_weights_yuan/*.pth 2>/dev/null
echo ""

# === 清理 ===
echo "VM 仍在運行 (費用 ~\$0.25/hr)"
read -p "停止 VM？(y/N) " stop_confirm
if [ "$stop_confirm" = "y" ] || [ "$stop_confirm" = "Y" ]; then
    gcloud compute instances stop "$INSTANCE_NAME" --zone="$ZONE" --quiet
    echo "VM 已停止"
    read -p "刪除 VM？(y/N) " delete_confirm
    if [ "$delete_confirm" = "y" ] || [ "$delete_confirm" = "Y" ]; then
        gcloud compute instances delete "$INSTANCE_NAME" --zone="$ZONE" --quiet
        echo "VM 已刪除"
    fi
fi

echo ""
echo "============================================================"
echo "  下一步: 設定本地推理"
echo "============================================================"
echo ""
echo "  1. 複製模型到 GPT-SoVITS 目錄:"
echo "     mkdir -p ~/GPT-SoVITS/GPT_weights/yuan ~/GPT-SoVITS/SoVITS_weights/yuan"
echo "     cp $MODEL_OUTPUT_DIR/GPT_weights_yuan/*.ckpt ~/GPT-SoVITS/GPT_weights/yuan/"
echo "     cp $MODEL_OUTPUT_DIR/SoVITS_weights_yuan/*.pth ~/GPT-SoVITS/SoVITS_weights/yuan/"
echo ""
echo "  2. 啟動 WebUI:"
echo "     cd ~/GPT-SoVITS && python webui.py"
echo ""
echo "  3. 在 WebUI 中載入模型進行推理"
echo "============================================================"
