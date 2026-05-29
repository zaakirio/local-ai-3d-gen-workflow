# 02 — Downloads: what to get and where it goes

All paths are relative to your ComfyUI install (`~/ComfyUI`). Use `hf download` (from `huggingface-hub`:
`uv pip install huggingface-hub`). `scripts/download_models.sh` automates this whole table.

> **License legend:** ✅ commercial-OK · 🔬 research/non-commercial only · ⚠️ restricted/region-locked.
> If you ever ship commercially, use only the ✅ rows.

---

## Stage 1 — Character image (text-to-image)

### Option A — Z-Image-Turbo ✅ (recommended for commercial; fast, ~8 steps)
| What | Repo / file | Folder |
|---|---|---|
| Model | `Tongyi-MAI/Z-Image-Turbo` (Apache-2.0) | per ComfyUI Z-Image template (native support) |

### Option B — FLUX.2-klein-9B GGUF 🔬 (non-commercial; higher fidelity)
| What | Repo / file | Folder |
|---|---|---|
| UNet (pick one) | `QuantStack/FLUX.2-Klein-9B-KV-GGUF` → `Flux-2-Klein-9B-KV-Q6_K.gguf` (7.87 GB) | `models/unet` |
| Text encoder | `Comfy-Org/flux2-dev` → `split_files/text_encoders/mistral_3_small_flux2_fp8.safetensors` | `models/text_encoders` |
| VAE | `Comfy-Org/flux2-dev` → `split_files/vae/` FLUX.2 VAE | `models/vae` |

> FLUX.2 uses **Mistral Small 3.1** as text encoder, not T5/CLIP. The fp8 encoder + Q6 UNet fit 16GB; bf16 encoder does not.
> klein-**4B** is Apache-2.0 if you want a commercial FLUX option instead.

### T-pose control (both options)
| What | Repo | Folder / node |
|---|---|---|
| ControlNet (Qwen base) | `InstantX/Qwen-Image-ControlNet-Union` (pose/canny/depth) | `models/controlnet` |
| Pose preprocessor | `Fannovel16/comfyui_controlnet_aux` (node: **DWPreprocessor**) | `custom_nodes/` |

> ControlNet is **model-specific**: the InstantX union is Qwen-only; for FLUX use a FLUX pose ControlNet. DWPose itself is model-agnostic (just extracts the skeleton).

---

## Stage 2 — Companion edit (palette-locked image edit)
| What | Repo / file | Folder |
|---|---|---|
| UNet | `QuantStack/Qwen-Image-Edit-2509-GGUF` → `…Q4_K_M.gguf` (13.1 GB) **or** `…Q5_K_S.gguf` (14.1 GB) | `models/unet` |
| Text encoder (Qwen2.5-VL) | `unsloth/Qwen2.5-VL-7B-Instruct-GGUF` → encoder GGUF **+ matching `mmproj-*.gguf`** | `models/text_encoders` |
| VAE | Qwen-Image VAE | `models/vae` |

> ⚠️ **Q6_K (16.8 GB) will NOT fit 16GB** with the VL encoder co-resident. Cap at Q4_K_M / Q5_K_S.
> The `mmproj` file is mandatory (vision projection) and must sit next to the encoder GGUF.

---

## Stage 3 — Background removal
| What | Repo / file | Folder / node |
|---|---|---|
| Node | `lldacing/ComfyUI_BiRefNet_ll` | `custom_nodes/` |
| Weights ✅ | `ZhengPeng7/BiRefNet` → `BiRefNet_HR` (`model.safetensors`, ~444 MB) | `models/BiRefNet/` (auto-downloads) |

> Use upstream **BiRefNet (MIT)**, **not** `briaai/RMBG-2.0` — RMBG-2.0 is non-commercial (paid Bria license).

---

## Stage 4 — Image → 3D mesh + texture
**Primary path for 16GB: Hunyuan3D 2.1 via the GPU-poor fork.**

| What | Repo | License |
|---|---|---|
| Weights | `tencent/Hunyuan3D-2.1` | ⚠️ `tencent-hunyuan-community` (region restrictions; verify) |
| Low-VRAM runtime | `deepbeepmeep/Hunyuan3D-2GP` (~6–9 GB; profiles 3/4) | — |
| ComfyUI node | `kijai/ComfyUI-Hunyuan3DWrapper` or `visualbruno/ComfyUI-Hunyuan3d-2-1` | — |

Stock Hunyuan3D 2.1 VRAM (official issue #15): **shape ~10 GB, paint ~21 GB, both ~29 GB.**
→ The **paint pass does NOT fit 16GB stock**; the `2GP` fork / `low_vram_mode` / lower `max_num_view` is mandatory.

**Alternatives:**
| Model | Repo | Note |
|---|---|---|
| TRELLIS.2-4B | `microsoft/TRELLIS.2-4B` (MIT, Dec 2025) | SOTA + PBR GLB, but **official min 24 GB** — experimental/offloaded only on 16GB |
| TRELLIS (original) | `microsoft/TRELLIS-image-large` (MIT) | Fits 16GB but RGB/Gaussian, **not full PBR** |
| TripoSG | `VAST-AI/TripoSG` (MIT) | Light, **geometry only** — bolt on a separate texture pass |
| Step1X-3D | `stepfun-ai/Step1X-3D` (Apache-2.0 ✅) | Cleanest license; geometry + SDXL texture (texture pass heavier) |

ComfyUI node covering several: `MrForExample/ComfyUI-3D-Pack`.

---

## Stage 5 — Rig + animation
**Pick by priority — there's a real trade-off (verified):**
- **Best rig + commercial + creatures → SkinTokens.** But its skeleton is **learned/unnamed**, so the
  animation step needs *positional* retargeting (harder).
- **Easiest animation → MIA.** Outputs a **mixamorig (named)** skeleton (drop-in for `bake_anim.py --direct`),
  but weights are **CC-BY-NC** (non-commercial only).

**SkinTokens** (VAST-AI, MIT, arXiv 2602.04805, Feb 2026): successor to UniRig; rigs **humanoids +
creatures**; **GLB in → rigged GLB out** in one shot; +98–133% skin / +17–22% bone vs prior SOTA.
Needs **≥14 GB VRAM** (fits 16GB only with display/other models NOT resident — run headless).
Python ≥3.11, CUDA ≥12.1, torch cu128.
```bash
git clone https://github.com/VAST-AI-Research/SkinTokens && cd SkinTokens
python download.py --model        # pulls VAST-AI/SkinTokens (2 ckpts: articulation_xl_* + skin_vae_*)
python demo.py --input mesh.glb --output rigged.glb
```

| What | Repo | Note |
|---|---|---|
| **SkinTokens (best rig)** | `github.com/VAST-AI-Research/SkinTokens` · HF `VAST-AI/SkinTokens` | MIT; humanoid + creature; rig+skin → GLB; CLI (no ComfyUI node yet). Skeleton is **predicted/unnamed** → retarget by position, not name. |
| **MIA (easiest animate)** | `jasongzy/Make-It-Animatable` | **mixamorig named skeleton** → `bake_anim.py --direct`; weights **CC-BY-NC** (non-commercial) |
| UniRig (fallback) | `github.com/VAST-AI-Research/UniRig` · weights `apozz/UniRig-safetensors` | MIT; skeleton + skin; FBX out → convert |
| ComfyUI node (UniRig/MIA) | `PozzettiAndrea/ComfyUI-UniRig` | bundles Blender + UniRig + MIA |
| Creature-only fallback | `Isabella98Liu/RigAnything` | template-free; restrictive license (SkinTokens covers creatures, so usually unneeded) |
| Bake named clips (free, GUI) | [mesh2motion.org](https://mesh2motion.org) (`Mesh2Motion/mesh2motion-app`, MIT) | human + animal skeletons, exports multi-clip GLB |
| Bake named clips (browser) | Mixamo (free, Adobe ID) → FBX | then convert ↓ |
| FBX → GLB | `godotengine/FBX2glTF` (linux-x64) | `FBX2glTF --binary --anim-framerate bake30 -i c.fbx -o c.glb` |

> See `docs/03-pipeline.md` for the exact rigging chain. The animation **bake** is the only non-headless step.

---

## Stage 6 — Floor PBR (image → basecolor/normal/roughness/metalness)
| What | Repo | License |
|---|---|---|
| CHORD node | `ubisoft/ComfyUI-Chord` | 🔬 research-only |
| CHORD weights | `Ubisoft/ubisoft-laforge-chord` → `chord_v1.safetensors` | 🔬 |
| Commercial alt | `qornflex/ComfyUI-QFX-PBRGenerator` (Marigold delight) | ✅ (verify) |
| Commercial alt | `amtarr/ComfyUI-TextureAlchemy` | ✅ (verify) |

---

## Stage 7 — Background video loop
**Wan 2.2 I2V is a dual-model (high+low noise) setup — you need both GGUFs.**

| What | Repo / file | Folder |
|---|---|---|
| High-noise UNet | `QuantStack/Wan2.2-I2V-A14B-GGUF` → `HighNoise/…HighNoise-Q4_K_M.gguf` (9.65 GB) | `models/unet` |
| Low-noise UNet | same repo → `LowNoise/…LowNoise-Q4_K_M.gguf` | `models/unet` |
| Text encoder | `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` → `split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders` |
| VAE | same repo → `split_files/vae/wan_2.1_vae.safetensors` | `models/vae` |
| Speed LoRA (4-step) | `lightx2v/Wan2.2-Lightning` → `…4steps…/high_noise_model.safetensors` + `low_noise_model.safetensors` | `models/loras` |
| Node | `city96/ComfyUI-GGUF` (native Wan) or `kijai/ComfyUI-WanVideoWrapper` | `custom_nodes/` |

> Run high-noise then low-noise **sequentially** (one in VRAM at a time) — Q8 (15.4 GB each) is too tight on 16GB.
> Apply the high LoRA to the high pass, low LoRA to the low pass. Loop trick: first frame == last frame.

**Lighter alternative — LTX-Video:** node `Lightricks/ComfyUI-LTXVideo`, GGUF `QuantStack/LTXV-13B-0.9.8-distilled-GGUF` → `models/unet`.

---

## Shared loader
| What | Repo | Install |
|---|---|---|
| GGUF loader (UNet + CLIP) | `city96/ComfyUI-GGUF` | clone to `custom_nodes/`, then `pip install --upgrade gguf` |

## Sources
See the per-stage source links in the research that produced this table — every repo above was confirmed live on 2026-05-29:
QuantStack (FLUX.2/Qwen/Wan GGUF), Comfy-Org (flux2-dev, Wan repackaged), Tongyi-MAI/Z-Image-Turbo, tencent/Hunyuan3D-2.1, deepbeepmeep/Hunyuan3D-2GP, microsoft/TRELLIS.2-4B, VAST-AI/TripoSG, stepfun-ai/Step1X-3D, PozzettiAndrea/ComfyUI-UniRig, jasongzy/Make-It-Animatable, Mesh2Motion, ubisoft/ComfyUI-Chord, ZhengPeng7/BiRefNet, lightx2v/Wan2.2-Lightning, city96/ComfyUI-GGUF, Fannovel16/comfyui_controlnet_aux.
