#!/bin/bash
# ============================================================
# GCP GPT-SoVITS 訓練環境 — 一鍵啟動腳本 (v2)
# 使用 Deep Learning VM Image + L4 GPU (Spot VM)
# ============================================================
#
# 使用方式:
#   1. 先設定你的 GCP project:
#      gcloud config set project YOUR_PROJECT_ID
#
#   2. 確認 GPU 配額:
#      gcloud compute regions describe asia-east1 --format="value(quotas)"
#
#   3. 執行此腳本:
#      bash gcp-gpt-sovits-setup.sh
#
# 費用估算 (Spot VM):
#   g2-standard-4 (1x L4, 4 vCPU, 16GB RAM): ~$0.25/hr
#   150GB SSD boot disk: ~$0.26/day
#   總計 3 小時訓練: ~$1-2 USD
# ============================================================

# === 配置變數 (可依需求修改) ===
INSTANCE_NAME="gpt-sovits-trainer"
ZONE="asia-east1-c"            # 台灣區域，低延遲
MACHINE_TYPE="g2-standard-4"   # 1x L4 GPU, 4 vCPU, 16GB RAM (GPU 是瓶頸，不需更多 CPU)
BOOT_DISK_SIZE="150"           # GB
IMAGE_PROJECT="deeplearning-platform-release"

# --- Pre-flight checks ---

# 檢查 GCP project
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
    echo "ERROR: 未設定 GCP project"
    echo "請執行: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# 動態偵測可用的 PyTorch GPU image family (含 CUDA)
echo "偵測最新 Deep Learning VM image..."
IMAGE_FAMILY=$(gcloud compute images list \
    --project="$IMAGE_PROJECT" \
    --filter="family:pytorch AND family:cu" \
    --format="value(family)" \
    --sort-by="~creationTimestamp" 2>/dev/null | head -1)

if [ -z "$IMAGE_FAMILY" ]; then
    # Fallback: 直接查所有 pytorch families
    IMAGE_FAMILY=$(gcloud compute images list \
        --project="$IMAGE_PROJECT" \
        --filter="family:pytorch" \
        --format="value(family)" \
        --sort-by="~creationTimestamp" 2>/dev/null | head -1)
fi

if [ -z "$IMAGE_FAMILY" ]; then
    echo "ERROR: 無法偵測可用的 PyTorch image family"
    exit 1
fi

# 驗證 image family 存在
if ! gcloud compute images describe-from-family "$IMAGE_FAMILY" \
    --project="$IMAGE_PROJECT" --format="value(name)" &>/dev/null; then
    echo "ERROR: Image family '$IMAGE_FAMILY' 不存在"
    echo "可用的 PyTorch families:"
    gcloud compute images list --project="$IMAGE_PROJECT" \
        --filter="family:pytorch" --format="value(family)" | sort -u
    exit 1
fi

echo ""
echo "=== GPT-SoVITS GCP 訓練環境設定 ==="
echo "Project:  $PROJECT"
echo "Instance: $INSTANCE_NAME"
echo "Zone:     $ZONE"
echo "Machine:  $MACHINE_TYPE (1x NVIDIA L4, 24GB VRAM)"
echo "Image:    $IMAGE_FAMILY"
echo "Disk:     ${BOOT_DISK_SIZE}GB SSD"
echo "Type:     Spot VM (省 60-70%)"
echo ""
read -p "費用約 \$0.25/hr，確認建立？(y/N) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# Cleanup trap
cleanup() {
    echo ""
    echo "腳本中斷。VM 可能已部分建立。"
    echo "刪除 VM: gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --quiet"
}
trap cleanup ERR

# === Step 1: 建立 Spot VM ===
echo ""
echo "[1/5] 建立 GCP Spot VM..."
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

echo "VM 建立成功，等待 NVIDIA 驅動安裝 (約 3-5 分鐘)..."

# === Step 2: 等待 SSH 就緒 ===
echo "[2/5] 等待 SSH 連線..."
sleep 30

SSH_READY=false
for i in $(seq 1 20); do
    if gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="echo ready" 2>/dev/null; then
        SSH_READY=true
        echo "SSH 連線成功!"
        break
    fi
    echo "  等待 SSH... ($i/20, 約 ${i}x15 秒)"
    sleep 15
done

if [ "$SSH_READY" != "true" ]; then
    echo "ERROR: SSH 連線逾時 (5 分鐘)"
    echo "請手動檢查: gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE"
    exit 1
fi

# === Step 3: 上傳安裝腳本到 VM (避免長 SSH session 斷線) ===
echo "[3/5] 上傳安裝腳本到 VM..."

# 建立遠端安裝腳本
INSTALL_SCRIPT=$(mktemp)
cat > "$INSTALL_SCRIPT" << 'INSTALL_EOF'
#!/bin/bash
set -eo pipefail

LOG="/tmp/gpt-sovits-install.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== GPT-SoVITS 安裝開始 $(date) ==="

# [a] 等待 NVIDIA 驅動
echo "[a] 等待 NVIDIA 驅動... (est. 1-3 min)"
for i in $(seq 1 30); do
    if nvidia-smi &>/dev/null; then
        echo "NVIDIA 驅動就緒!"
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

# [b] 系統依賴
echo "[b] 安裝系統依賴... (est. 1 min)"
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg libsndfile1 git-lfs tmux

# [c] Clone GPT-SoVITS
echo "[c] Clone GPT-SoVITS... (est. 1-2 min)"
cd ~
if [ ! -d "GPT-SoVITS" ]; then
    git clone --depth 1 https://github.com/RVC-Boss/GPT-SoVITS.git
fi
cd GPT-SoVITS

# [d] 使用 conda 環境 (保留 Deep Learning VM 的 CUDA 配置)
echo "[d] 設定 Python 環境... (est. 3-5 min)"
# Deep Learning VM 已有 conda，直接用
if command -v conda &>/dev/null; then
    echo "使用 conda..."
    eval "$(conda shell.bash hook)"
    conda create -n gptsovits python=3.10 -y 2>/dev/null || true
    conda activate gptsovits
    # 安裝 PyTorch with CUDA (匹配 Deep Learning VM 的 CUDA 版本)
    CUDA_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    echo "CUDA driver: $CUDA_VER"
    pip install --upgrade pip
    if [ -f "extra-req.txt" ]; then
        pip install -r extra-req.txt --no-deps || true
    fi
    pip install -r requirements.txt
else
    echo "conda 未找到，使用 pip..."
    pip install --upgrade pip
    if [ -f "extra-req.txt" ]; then
        pip install -r extra-req.txt --no-deps || true
    fi
    pip install -r requirements.txt
fi

# [e] 下載預訓練模型 (完整下載，不過濾副檔名)
echo "[e] 下載預訓練模型... (est. 5-10 min)"
pip install huggingface_hub

# 檢查磁碟空間
AVAILABLE=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
echo "可用磁碟空間: ${AVAILABLE}GB"
if [ "$AVAILABLE" -lt 30 ]; then
    echo "WARNING: 磁碟空間不足 30GB，模型下載可能失敗"
fi

python3 << 'PYEOF'
from huggingface_hub import snapshot_download
import os

print("下載 GPT-SoVITS pretrained models...")
snapshot_download(
    repo_id='lj1995/GPT-SoVITS',
    local_dir='GPT_SoVITS/pretrained_models',
    # 下載所有檔案，只排除文件類
    ignore_patterns=['*.md', '.gitattributes', 'LICENSE*']
)
print("預訓練模型下載完成!")

# 驗證關鍵檔案
critical_files = [
    'GPT_SoVITS/pretrained_models/gsv-v2final-pretrained',
    'GPT_SoVITS/pretrained_models/chinese-hubert-base',
    'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large',
]
for f in critical_files:
    if os.path.exists(f):
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ MISSING: {f}")
PYEOF

# [f] 建立訓練資料目錄
echo "[f] 建立目錄結構..."
mkdir -p ~/training_data/audio
mkdir -p ~/training_data/output

# [g] 建立啟動腳本
cat > ~/start-webui.sh << 'WEBUI_EOF'
#!/bin/bash
cd ~/GPT-SoVITS
eval "$(conda shell.bash hook)" 2>/dev/null
conda activate gptsovits 2>/dev/null
python webui.py
WEBUI_EOF
chmod +x ~/start-webui.sh

echo ""
echo "========================================="
echo "  GPT-SoVITS 安裝完成! $(date)"
echo "========================================="
echo "  啟動: ~/start-webui.sh"
echo "  日誌: $LOG"
echo "========================================="
INSTALL_EOF

# 上傳安裝腳本
gcloud compute scp "$INSTALL_SCRIPT" "$INSTANCE_NAME":/tmp/install-gptsovits.sh --zone="$ZONE"
rm -f "$INSTALL_SCRIPT"

# 在 tmux 中執行 (防止 SSH 斷線中斷安裝)
echo "[3/5] 在 VM 上啟動安裝 (tmux 背景執行，防斷線)..."
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="
    chmod +x /tmp/install-gptsovits.sh
    tmux new-session -d -s install 'bash /tmp/install-gptsovits.sh; echo DONE > /tmp/install-done'
"

echo "安裝已在背景執行，等待完成..."
echo "  (可另開終端查看進度: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- 'tmux attach -t install')"
echo ""

# 等待安裝完成 (輪詢)
for i in $(seq 1 120); do
    if gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="test -f /tmp/install-done" 2>/dev/null; then
        echo "安裝完成!"
        break
    fi
    # 每 30 秒顯示一次進度
    if [ $((i % 2)) -eq 0 ]; then
        PROGRESS=$(gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" \
            --command="tail -1 /tmp/gpt-sovits-install.log 2>/dev/null" 2>/dev/null || echo "等待中...")
        echo "  [$((i/2)) min] $PROGRESS"
    fi
    sleep 30
done

if ! gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="test -f /tmp/install-done" 2>/dev/null; then
    echo "WARNING: 安裝超時 (60 min)，可能仍在執行中"
    echo "手動查看: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- 'tmux attach -t install'"
fi

# === Step 4: 上傳訓練資料 ===
echo "[4/5] 上傳訓練資料到 VM..."

YUAN_PROJECT="$HOME/Projects/yuan-voice-clone"

# 上傳所有可用的訓練資料
UPLOADED=false

# 優先上傳 gpt-sovits-training 目錄 (已整理好的資料)
if [ -d "$YUAN_PROJECT/gpt-sovits-training/audio" ]; then
    echo "上傳 gpt-sovits-training/audio/..."
    gcloud compute scp --recurse \
        "$YUAN_PROJECT/gpt-sovits-training/audio" \
        "$INSTANCE_NAME":~/training_data/ --zone="$ZONE"
    UPLOADED=true
fi

# 上傳標註文件
for f in "$YUAN_PROJECT/gpt-sovits-training"/*.list; do
    if [ -f "$f" ]; then
        echo "上傳標註: $(basename "$f")"
        gcloud compute scp "$f" "$INSTANCE_NAME":~/training_data/ --zone="$ZONE"
        UPLOADED=true
    fi
done

# 也上傳 zip 包 (如果存在)
if [ -f "$YUAN_PROJECT/gpt-sovits-training/yuan_training_data.zip" ]; then
    echo "上傳 yuan_training_data.zip..."
    gcloud compute scp "$YUAN_PROJECT/gpt-sovits-training/yuan_training_data.zip" \
        "$INSTANCE_NAME":~/training_data/ --zone="$ZONE"
    UPLOADED=true
fi

# Fallback: 上傳 clean_chunks
if [ "$UPLOADED" != "true" ] && [ -d "$YUAN_PROJECT/clean_chunks" ]; then
    echo "上傳 clean_chunks/..."
    gcloud compute scp --recurse \
        "$YUAN_PROJECT/clean_chunks" \
        "$INSTANCE_NAME":~/training_data/audio/ --zone="$ZONE"
    UPLOADED=true
fi

if [ "$UPLOADED" != "true" ]; then
    echo "WARNING: 未找到訓練資料，請手動上傳:"
    echo "  gcloud compute scp --recurse YOUR_AUDIO_DIR $INSTANCE_NAME:~/training_data/audio/ --zone=$ZONE"
fi

# === Step 5: 完成 ===
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "pending")

echo ""
echo "============================================================"
echo "  設定完成!"
echo "============================================================"
echo ""
echo "  VM 名稱:     $INSTANCE_NAME"
echo "  外部 IP:     $EXTERNAL_IP"
echo "  GPU:         NVIDIA L4 (24GB VRAM)"
echo "  費用:        ~\$0.25/hr (Spot)"
echo "  安裝日誌:    /tmp/gpt-sovits-install.log (VM 上)"
echo ""
echo "  連線方式:"
echo "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "  啟動 WebUI (SSH 進去後):"
echo "    ~/start-webui.sh"
echo ""
echo "  安全存取 WebUI (SSH tunnel，不需開防火牆):"
echo "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- -L 9874:localhost:9874"
echo "    然後瀏覽器開啟: http://localhost:9874"
echo ""
echo "  訓練完成後關閉 VM 省錢:"
echo "    gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "  刪除 VM:"
echo "    gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE"
echo "============================================================"
