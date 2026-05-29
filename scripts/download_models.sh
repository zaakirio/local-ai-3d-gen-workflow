#!/usr/bin/env bash
# download_models.sh — pull every weight to its ComfyUI folder. Verified repos as of 2026-05-29.
# Requires: huggingface-hub (`uv pip install huggingface-hub`), and `hf auth login` for gated repos.
# Toggle stages with the flags below; comment out what you don't need (weights are large).
set -euo pipefail

: "${COMFY:=$HOME/ComfyUI}"
M="$COMFY/models"
mkdir -p "$M"/{unet,text_encoders,vae,controlnet,loras,BiRefNet,diffusion_models}

# Which stages to fetch (1=yes 0=no)
DL_IMAGE_COMMERCIAL=1   # Z-Image-Turbo (Apache-2.0)
DL_IMAGE_FLUX=0         # FLUX.2-klein-9B GGUF (NON-COMMERCIAL)
DL_QWEN_EDIT=1
DL_CONTROLNET=1
DL_BIREFNET=1
DL_WAN=1
DL_HUNYUAN=1            # large + gated-ish (tencent-hunyuan-community license)

dl() { echo "== $1"; hf download "$@"; }   # hf download <repo> [files...] --local-dir ...

# --- Stage 1: character image ---
if [[ $DL_IMAGE_COMMERCIAL == 1 ]]; then
  dl Tongyi-MAI/Z-Image-Turbo --local-dir "$M/diffusion_models/Z-Image-Turbo"
fi
if [[ $DL_IMAGE_FLUX == 1 ]]; then
  dl QuantStack/FLUX.2-Klein-9B-KV-GGUF Flux-2-Klein-9B-KV-Q6_K.gguf --local-dir "$M/unet"
  dl Comfy-Org/flux2-dev split_files/text_encoders/mistral_3_small_flux2_fp8.safetensors --local-dir "$M/text_encoders"
  # FLUX.2 VAE:
  dl Comfy-Org/flux2-dev --include "split_files/vae/*" --local-dir "$M/vae"
fi

# --- Stage 1 control: T-pose ---
if [[ $DL_CONTROLNET == 1 ]]; then
  dl InstantX/Qwen-Image-ControlNet-Union --local-dir "$M/controlnet/Qwen-ControlNet-Union"
  # DWPose preprocessor weights are pulled by comfyui_controlnet_aux on first run.
fi

# --- Stage 2: companion edit ---
if [[ $DL_QWEN_EDIT == 1 ]]; then
  dl QuantStack/Qwen-Image-Edit-2509-GGUF Qwen-Image-Edit-2509-Q4_K_M.gguf --local-dir "$M/unet"
  # Qwen2.5-VL text encoder + REQUIRED mmproj (vision projection):
  dl unsloth/Qwen2.5-VL-7B-Instruct-GGUF --include "*Q4_K_M*.gguf" "mmproj*.gguf" --local-dir "$M/text_encoders"
  echo "   NOTE: also place the Qwen-Image VAE in $M/vae"
fi

# --- Stage 3: background removal ---
if [[ $DL_BIREFNET == 1 ]]; then
  dl ZhengPeng7/BiRefNet_HR --local-dir "$M/BiRefNet/BiRefNet_HR"   # MIT, commercial-OK
fi

# --- Stage 4: image -> 3D (Hunyuan3D 2.1) ---
if [[ $DL_HUNYUAN == 1 ]]; then
  echo "== tencent/Hunyuan3D-2.1 (accept the tencent-hunyuan-community license on HF first; region-restricted)"
  dl tencent/Hunyuan3D-2.1 --local-dir "$COMFY/models/hunyuan3d/Hunyuan3D-2.1"
fi

# --- Stage 5: rigging weights ---
echo "== rigging weights (UniRig + MIA) — ComfyUI-UniRig usually auto-pulls these on first run:"
echo "     apozz/UniRig-safetensors  +  jasongzy/Make-It-Animatable"

# --- Stage 7: background video (Wan 2.2 I2V — BOTH high & low noise) ---
if [[ $DL_WAN == 1 ]]; then
  dl QuantStack/Wan2.2-I2V-A14B-GGUF HighNoise/Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf --local-dir "$M/unet"
  dl QuantStack/Wan2.2-I2V-A14B-GGUF LowNoise/Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf  --local-dir "$M/unet"
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors --local-dir "$M/text_encoders"
  dl Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan_2.1_vae.safetensors --local-dir "$M/vae"
  dl lightx2v/Wan2.2-Lightning --include "*4steps*rank64*/*.safetensors" --local-dir "$M/loras/Wan2.2-Lightning"
fi

echo
echo "Done. PBR (Stage 6): CHORD weights -> Ubisoft/ubisoft-laforge-chord (research-only); fetch manually if needed."
echo "Verify VRAM-fit notes in docs/02-downloads.md (Qwen edit: stay <=Q5; Wan: run one noise model at a time)."
