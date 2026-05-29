# 01 — Arch Linux + Blackwell (sm_120) setup

Target: **RTX 5060 Ti 16GB** (Blackwell, compute capability `sm_120`), i9-12900K, 32GB RAM.
This is the part that takes the longest. Budget ~a day, mostly compiling 3D CUDA kernels.

> The golden rule for everything below: **pin one torch build, set `TORCH_CUDA_ARCH_LIST="12.0"`,
> and build every native CUDA kernel from source against that one torch.** Mixing prebuilt
> wheels across torch versions is the #1 cause of "no kernel image available" / ABI load failures.

## 1. System packages (pacman)
```bash
# Blackwell REQUIRES the open kernel modules. The legacy proprietary `nvidia` will not do sm_120.
sudo pacman -S nvidia-open-dkms nvidia-utils
sudo pacman -S cuda            # toolkit + nvcc (needed to COMPILE the 3D kernels), lands in /opt/cuda
sudo pacman -S base-devel git cmake ninja
sudo pacman -S nodejs npm      # for gltf-transform (the compression stage)
sudo pacman -S blender         # for the headless retopo + animation-bake glue (or use AUR/flatpak)
reboot                          # load the new kernel module
nvidia-smi                      # must show the 5060 Ti and CUDA >= 12.8
```

### GCC gotcha (classic Arch + CUDA)
Arch's GCC is usually **too new for nvcc**. If a kernel build throws `unsupported GNU version`:
```bash
# from AUR (e.g. yay)
yay -S gcc14
export CUDAHOSTCXX=/usr/bin/g++-14
```
You hit this exactly when building `pytorch_scatter` / `custom_rasterizer` / `kaolin`.

## 2. Environment (do NOT use system Python)
Arch ships Python 3.13+, which outruns many ML wheels. Pin 3.12 in an isolated env:
```bash
# uv is cleanest; micromamba/conda also fine
uv venv --python 3.12 ~/envs/gen3d
source ~/envs/gen3d/bin/activate

# Blackwell needs cu128 minimum; cu130 is the current recommended channel.
# Stable cu128 now ships sm_120 kernels; nightly cu130 is the freshest.
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

python - <<'PY'
import torch
print("torch", torch.__version__, "| cuda", torch.version.cuda)
print("device", torch.cuda.get_device_name(0))
print("sm_120 in arch list:", "sm_120" in torch.cuda.get_arch_list())
PY
```
`sm_120 in arch list: True` is the gate. If False, your torch wheel has no Blackwell kernels — fix this before anything else.

> ⚠️ **Never install `xformers` or `flash-attn` with default deps** — they silently downgrade torch
> back to a stable build without sm_120 and break the whole stack. If you need them: `pip install ... --no-deps`.
> ComfyUI runs fine on PyTorch attention without xformers.

## 3. ComfyUI
```bash
git clone https://github.com/comfyanonymous/ComfyUI ~/ComfyUI
cd ~/ComfyUI
uv pip install -r requirements.txt
# sanity launch (Ctrl-C after it reports the device)
python main.py --listen 127.0.0.1 --port 8188
```

Install **ComfyUI-Manager** (makes adding the rest one-click) then the custom nodes —
all of this is scripted in `scripts/install.sh`.

## 4. The 3D CUDA kernels (the hard part)
Hunyuan3D / TRELLIS / 3D-Pack compile native kernels. Build them **in the gen3d env** with arch set:
```bash
source ~/envs/gen3d/bin/activate
export TORCH_CUDA_ARCH_LIST="12.0"        # sm_120 — required, or you get "no kernel image available" at runtime
export CUDA_HOME=/opt/cuda
export CUDAHOSTCXX=/usr/bin/g++-14         # only if nvcc rejects system gcc
```
Kernels you will likely build from source: `custom_rasterizer` (Hunyuan paint), `nvdiffrast`,
`diff-gaussian-rasterization`, `pytorch_scatter` (torch-scatter), `kaolin`.

Known pain points (verified, mid-2026):
- **`pytorch_scatter`** — `std ambiguous symbol` / `sm_120 not defined` if your nvcc is older than CUDA 12.8. Use the `cuda` package's nvcc (12.8+).
- **`kaolin`** — no prebuilt sm_120 wheels; build from source against your exact torch.
- **`nvdiffrast`** — JIT-builds at first run; fine once `TORCH_CUDA_ARCH_LIST` includes 12.0.
- **kijai's `ComfyUI-Hunyuan3DWrapper`** ships prebuilt wheels that are **Windows-only (cp312/cu126)** — on Linux ignore them and build `custom_rasterizer`/`mesh_processor` from its `hy3dgen/.../custom_rasterizer` source dir.

## 5. Node / npm tooling
```bash
npm i -g @gltf-transform/cli         # resize -> webp -> draco, identical to the cloud step
# FBX2glTF for the Mixamo path (precompiled linux-x64):
#   https://github.com/godotengine/FBX2glTF  (more actively maintained fork)
```

## Verify-before-you-commit checklist
- [ ] `nvidia-smi` shows the card + CUDA ≥ 12.8
- [ ] `sm_120 in torch arch list: True`
- [ ] ComfyUI launches and reports the GPU
- [ ] At least one 3D kernel (`custom_rasterizer`) imports without "no kernel image available"
- [ ] Recheck the [Comfy-Org Blackwell thread](https://github.com/Comfy-Org/ComfyUI/discussions/6643) and [PyTorch sm_120 issue #164342](https://github.com/pytorch/pytorch/issues/164342) for the current best torch channel

## Sources
- [Comfy-Org Blackwell (50-series) support thread #6643](https://github.com/Comfy-Org/ComfyUI/discussions/6643)
- [ComfyUI system requirements (cu130)](https://docs.comfy.org/installation/system_requirements)
- [PyTorch sm_120 support issue #164342](https://github.com/pytorch/pytorch/issues/164342)
- [pytorch_scatter sm_120 build thread](https://discuss.pytorch.org/t/urgent-help-needed-compiling-pytorch-scatter-for-rtx-5070-in-comfyui-std-ambiguous-symbol-error/222742)
