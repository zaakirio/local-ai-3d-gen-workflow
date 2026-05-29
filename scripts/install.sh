#!/usr/bin/env bash
# install.sh — ComfyUI + custom nodes for the local-ai-3d-gen pipeline (Arch Linux, sm_120).
# Run AFTER the system/toolchain setup in docs/01-setup-arch.md and with the gen3d venv active.
set -euo pipefail

: "${COMFY:=$HOME/ComfyUI}"
: "${VENV:=$HOME/envs/gen3d}"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Activate the venv first:  source $VENV/bin/activate" >&2
  exit 1
fi

export TORCH_CUDA_ARCH_LIST="12.0"          # sm_120 — required for kernel builds
export CUDA_HOME="${CUDA_HOME:-/opt/cuda}"
# export CUDAHOSTCXX=/usr/bin/g++-14        # uncomment if nvcc rejects system gcc

# --- ComfyUI core ---
if [[ ! -d "$COMFY" ]]; then
  git clone https://github.com/comfyanonymous/ComfyUI "$COMFY"
fi
cd "$COMFY"
uv pip install -r requirements.txt
uv pip install huggingface-hub                # for hf download

NODES="$COMFY/custom_nodes"
mkdir -p "$NODES"
clone() { [[ -d "$NODES/$(basename "$1")" ]] || git clone "$1" "$NODES/$(basename "$1")"; }

# --- Custom nodes (one per stage) ---
clone https://github.com/ltdrdata/ComfyUI-Manager
clone https://github.com/city96/ComfyUI-GGUF                  # GGUF UNet/CLIP loaders (FLUX.2, Qwen, Wan)
clone https://github.com/Fannovel16/comfyui_controlnet_aux    # DWPose preprocessor (T-pose)
clone https://github.com/lldacing/ComfyUI_BiRefNet_ll         # background removal
clone https://github.com/kijai/ComfyUI-Hunyuan3DWrapper       # image->3D (Hunyuan3D 2.1)
clone https://github.com/MrForExample/ComfyUI-3D-Pack         # TRELLIS / multi-model 3D
clone https://github.com/PozzettiAndrea/ComfyUI-UniRig        # auto-rig (UniRig + MIA)
clone https://github.com/kijai/ComfyUI-WanVideoWrapper        # image->video (Wan 2.2)
clone https://github.com/ubisoft/ComfyUI-Chord                # PBR material extract (research-only)
# commercial PBR alt: clone https://github.com/qornflex/ComfyUI-QFX-PBRGenerator

# --- gguf runtime ---
uv pip install --upgrade gguf

echo
echo ">>> Node requirements: install each node's requirements.txt (some compile sm_120 kernels)."
for d in "$NODES"/*/; do
  if [[ -f "$d/requirements.txt" ]]; then
    echo "    uv pip install -r ${d}requirements.txt"
  fi
done
echo
echo ">>> The 3D nodes (Hunyuan3DWrapper, 3D-Pack, UniRig) build native CUDA kernels."
echo "    Build them from source with TORCH_CUDA_ARCH_LIST=12.0 set — see docs/01-setup-arch.md §4."
echo ">>> gltf-transform:  npm i -g @gltf-transform/cli"
echo ">>> Then download weights:  scripts/download_models.sh"
