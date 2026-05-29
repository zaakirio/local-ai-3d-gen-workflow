# 04 — OS choice: Arch vs Windows vs WSL2

Verified 2026-05-29 for an **RTX 5060 Ti 16GB (Blackwell, sm_120)**. Short version:
**run the generation pipeline on Linux.** Windows is equal for image/video alone but worse once
image-to-3D is involved. Its one real advantage (AccuRIG) helps rigging but can't ship in an OSS repo.

## Why Linux wins the generation pipeline
- **3D CUDA kernels** (`custom_rasterizer`, `nvdiffrast`, `torch-scatter`, `kaolin`): no Blackwell
  sm_120 prebuilt **Windows** wheels — kijai's are cu126/torch260, unusable on the cu128+ torch a
  5060 Ti needs. You compile regardless, and Windows MSVC builds hit the still-open
  `C2872 'std' ambiguous symbol` error (torch > 2.8.0). gcc on Linux avoids the whole class.
- **Attention backends**: Triton / FlashAttention are Linux-first. SageAttention 2.2 now has Windows
  Blackwell wheels (~30% faster) but with reported 50-series instability.
- Image gen + Wan video alone: Windows portable (bundled cu128) is roughly equal and easy to
  first-pixel — but the 3D leg is the deciding factor, and it favors Linux.

## The one genuine Windows benefit: AccuRIG 2
Free, Windows-native auto-rigger. For **humanoids** it removes this repo's fragile retarget step
(`bake_anim.py` rest-pose/bone-roll alignment) and has 4,500+ in-app ActorCore motions. But:
- Exports **FBX/USD only — no GLB** (still a Blender conversion pass).
- **Humanoid-strong, creature-weak** — UniRig may rig odd companions better.
- ⚠️ **Not OSS-redistributable:** Reallusion's EULA bars distributing ActorCore/Mixamo motion
  content as standalone/raw GLB. AccuRIG may rig *your* mesh, but its bundled clips can't ship here.

→ Use AccuRIG only as an **optional cross-boot helper** for personal/non-redistributed humanoid rigs.
Keep **UniRig + `bake_anim.py` + CC0 clips** as the shippable path.

## WSL2 — the middle path if you'd rather stay in Windows
GPU passthrough gives near-native CUDA, gcc compiles, Triton, FlashAttention, stable SageAttention —
i.e. Linux's wins without leaving Windows. Downsides:
- **OpenGL/EGL is flaky**: nvdiffrast's **GL** backend / 3D-Pack GL-interop fail under WSL2 (CUDA 304).
  Use nvdiffrast's **CUDA** backend; headless Blender works via CUDA/OptiX.
- Keep models on the **ext4** side (`~/`), not `/mnt/c` (slow cross-OS IO).
- Slight VRAM/RAM overhead vs native — fine on 16GB at these resolutions.

## Decision
| You want… | Use |
|---|---|
| Max performance + clean headless Blender/GL | **Native Arch** |
| Stay on one Windows install, accept GL quirks | **WSL2 Ubuntu** |
| Easier humanoid rig for a *personal* character | Arch/WSL2 generate → **reboot to AccuRIG** → FBX→GLB |
| Native Windows for the whole pipeline | **Not recommended** (3D-kernel compile pain) |

Storage note: 500GB is ample (full model set ~100–200GB); not a factor in the choice.

## Sources
- [ComfyUI Blackwell support #6643](https://github.com/Comfy-Org/ComfyUI/discussions/6643) · [kijai Hunyuan3DWrapper #181](https://github.com/kijai/ComfyUI-Hunyuan3DWrapper/issues/181) · [Hunyuan3DWrapper-Linux fork](https://github.com/VisionExp/ComfyUI-Hunyuan3DWrapper-Linux)
- [C2872 std ambiguous symbol (pytorch #173232)](https://github.com/pytorch/pytorch/issues/173232) · [SageAttention/Triton on Windows #11583](https://github.com/Comfy-Org/ComfyUI/discussions/11583)
- [NVIDIA CUDA-on-WSL2 guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html) · [3D-Pack WSL2 GL-interop #425](https://github.com/MrForExample/ComfyUI-3D-Pack/issues/425)
- [AccuRIG 2.0 (free, Windows-only)](https://www.cgchannel.com/2025/07/rig-and-animate-3d-characters-for-free-with-accurig-2-0/) · [AccuRIG export (FBX/USD)](https://manual.reallusion.com/AccuRig-2/2.0/09-add-motions/export.htm) · [Reallusion Content EULA](https://www.reallusion.com/Content/EULA/EULA.htm) · [UniRig](https://github.com/VAST-AI-Research/UniRig)
