# local-ai-3d-gen

A **fully local, open-weight** reproduction of the [fal-regenerate-3d](https://fal-roster.vercel.app)
pipeline — the cloud recipe that generates rigged 3D characters, companion creatures, PBR floors and
looped video backgrounds for an interactive Three.js character selector.

**What this achieves:** every generative stage of that pipeline runs on **one consumer GPU** with no
paid API calls and no data leaving the machine. Image generation, image-to-3D, rigging + baked
animation, PBR materials, and background video are all replaced by open-weight models driven through a
local **ComfyUI**. The Three.js front-end and `gltf-transform` compression are unchanged from the cloud build.

> Reproduced and documented on: **RTX 5060 Ti 16GB · i9-12900K · 32GB RAM · Arch Linux**.
> Other GPUs/distros should work but aren't what these notes were verified against.

## Pipeline (cloud → local)

| Stage | fal.ai cloud | Local replacement |
|---|---|---|
| Character image (T-pose) | gpt-image-2 / flux-2-klein | **Z-Image-Turbo** (commercial) / **FLUX.2-klein-9B GGUF** + DWPose ControlNet |
| Companion edit | gpt-image-2/edit | **Qwen-Image-Edit-2509 GGUF** |
| Background removal | bria | **BiRefNet** (MIT) |
| Image → 3D mesh + texture | meshy/v6 | **Hunyuan3D 2.1** (`Hunyuan3D-2GP` low-VRAM fork) |
| Rig + baked animation | meshy/v6 | **SkinTokens** (MIT, rig+skin→GLB) → Blender headless retarget + bake ([`bake_anim.py`](scripts/bake_anim.py)) |
| Floor PBR | patina | **CHORD** (research) / **QFX-PBRGenerator** (commercial) |
| Background video loop | seedance-2.0 | **Wan 2.2 I2V GGUF** + Lightning LoRA |
| Compression | gltf-transform | **gltf-transform** — unchanged |

Full per-stage model list, repos and VRAM notes: **[docs/02-downloads.md](docs/02-downloads.md)**.

## Quickstart
```bash
# 1. Set up the GPU/Python toolchain (Blackwell sm_120) — see docs/01-setup-arch.md
# 2. Install ComfyUI + custom nodes
scripts/install.sh
# 3. Download model weights (per-stage toggles inside)
scripts/download_models.sh
# 4. Build each stage's ComfyUI workflow once, export to comfyui-workflows/ (see its README)
# 5. Generate a character
python scripts/orchestrate.py --char-id neon01 --prompt "cyberpunk operative, full body T-pose, ..."
```

## Docs
- **[docs/01-setup-arch.md](docs/01-setup-arch.md)** — Arch + Blackwell sm_120 toolchain (the long, one-time part)
- **[docs/02-downloads.md](docs/02-downloads.md)** — every model: repo, file, target folder, license
- **[docs/03-pipeline.md](docs/03-pipeline.md)** — stage-by-stage flow, the rigging recipe, risk table
- **[docs/04-os-choice.md](docs/04-os-choice.md)** — Arch vs Windows vs WSL2 (verified: Linux wins for the 3D leg)
- **[comfyui-workflows/README.md](comfyui-workflows/README.md)** — how to export the per-stage workflow JSONs

## Honest caveats
- **One real fragile step:** rigging retarget (rest-pose/bone-roll alignment). It's headless and
  scripted, but validate your first character visually before batching. Details in docs/03.
- **No concurrency:** one GPU = serial. ~10–20 min/character, ~2–3 h for a 10-character roster
  (cloud was ~1 min / ~$1.20 each). Local wins on cost-at-scale, privacy, and free iteration.
- **Licensing for redistribution:** some defaults are non-commercial (FLUX.2-9B, CHORD, RMBG-2.0).
  Commercial-safe swaps are noted per stage (Z-Image, QFX, BiRefNet; SkinTokens rigging is MIT).
  Each model keeps its own license; this repo's own code is MIT.
