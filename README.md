# local-ai-3d-gen

A fully-local port of the **fal-regenerate-3d** pipeline (the cloud recipe behind
[fal-roster.vercel.app](https://fal-roster.vercel.app)) to open-weight AI running
on **one RTX 5060 Ti 16GB**, on **Arch Linux**.

The cloud version fans out paid fal.ai calls via the genmedia CLI. This port replaces
each generative stage with an open-weight model driven through a local **ComfyUI** instance,
and keeps the final Three.js page + `gltf-transform` compression **unchanged**.

> **Verified:** 2026-05-29. Model repos / VRAM figures are from official sources; see each
> doc's Sources. Re-check before downloading — the Blackwell/PyTorch stack moves fast.

---

## The swap (cloud → local)

| Stage | fal.ai cloud | Local replacement | Fits 16GB? |
|---|---|---|---|
| Character image (T-pose) | gpt-image-2 / flux-2-klein | **Z-Image-Turbo** (commercial) or **FLUX.2-klein-9B GGUF** (non-comm) + DWPose ControlNet | ✅ |
| Companion edit (palette-lock) | gpt-image-2/edit | **Qwen-Image-Edit-2509 GGUF** (Q4/Q5) | ✅ |
| Background removal | bria | **BiRefNet** (MIT) | ✅ trivial |
| Image → 3D mesh + texture | meshy/v6 (geometry) | **Hunyuan3D 2.1** via `Hunyuan3D-2GP` fork | ✅ (fork) |
| **Rig + animation** | meshy/v6 (rig+anim) | **ComfyUI-UniRig** (MIA path) + Blender/Mixamo to bake clips | ⚠️ see below |
| Floor PBR | patina | **CHORD** (research) / **QFX-PBRGenerator** (commercial) | ✅ |
| Background video loop | seedance-2.0 | **Wan 2.2 I2V A14B GGUF** + Lightning LoRA | ✅ (Q4/Q5, one pass at a time) |
| Compression | gltf-transform | **gltf-transform** — byte-identical, unchanged | ✅ (CPU) |

## The one real gap: rigging + animation
Meshy bakes **rig + skin + named idle/dance/alert clips into one GLB in a single call.**
Nothing local does that in one shot. Locally it's: mesh → retopo → auto-rig (UniRig/MIA) →
apply + bake a named clip (Blender headless or Mixamo) → export GLB. Expect a **manual cleanup
pass per character**, and worse for non-humanoid companions. This is the stage to consider
keeping on cloud Meshy if you ever go high-volume. See `docs/03-pipeline.md`.

## Docs
1. **[docs/01-setup-arch.md](docs/01-setup-arch.md)** — Arch + Blackwell sm_120 toolchain (the part that eats a day)
2. **[docs/02-downloads.md](docs/02-downloads.md)** — every model: exact repo, file, and target folder
3. **[docs/03-pipeline.md](docs/03-pipeline.md)** — stage-by-stage how-to, the rigging workaround, risks

## Scripts
- `scripts/install.sh` — system packages, ComfyUI, custom nodes
- `scripts/download_models.sh` — pulls every weight to the right folder via `hf download`
- `scripts/orchestrate.py` — drives ComfyUI's HTTP/WS API stage-by-stage, unloading between stages
- `comfyui-workflows/` — per-stage workflow JSONs (see that folder's README — you export these from the nodes' bundled examples)

## Reality check
| | Cloud (fal) | Local (5060 Ti 16GB) |
|---|---|---|
| Per character | ~1 min, ~$1.20 | ~10–20 min, serial |
| 10-char roster | ~10 min (9-way fan-out) | ~2–3 hours |
| Setup | zero | ~1 day (sm_120 kernel builds) |
| Wins | speed, concurrency | cost at scale, privacy, free iteration, deterministic pose control |

**Recommended:** start with the **one-character vertical slice** in `docs/03-pipeline.md` to
de-risk the two unknowns (kernel compile + rigging quality) before industrializing.
