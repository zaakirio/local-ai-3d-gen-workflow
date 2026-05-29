# 03 — Pipeline: stage-by-stage, the rigging workaround, and risks

This is the local equivalent of the fal-regenerate-3d pipeline. Each generative stage is a
ComfyUI workflow; `scripts/orchestrate.py` queues them in order and **unloads each model before
the next** (one 16GB card cannot hold two stages co-resident).

## Per-character flow
```
1. txt2img    Z-Image / FLUX.2-klein + DWPose ControlNet  -> character.png (1024x1536 T-pose)
2. cutout     BiRefNet                                     -> character_cut.png
3. img-edit   Qwen-Image-Edit-2509  (palette-locked)       -> companion.png -> cutout
4. img2mesh   Hunyuan3D 2.1 (2GP)   shape + paint          -> character.glb (textured)
5. retopo     Blender headless (decimate/remesh)           -> character_lo.glb
6. rig+anim   UniRig/MIA -> bake named clip                -> character_rigged.glb
7. floor PBR  CHORD / QFX                                  -> basecolor/normal/rough/metal
8. bg video   Wan 2.2 I2V (high->low noise) + Lightning    -> bg_loop.mp4 (8s, first==last frame)
9. compress   gltf-transform  resize1024 -> webp q80 -> draco
```
Then assemble into the existing Three.js HTML exactly as the cloud build does (palette CSS vars,
floor swap, mirror reflection, breathing) — that front-end code is unchanged.

## The VRAM sequencing rule
Stages 1, 3, 4, 8 each use a different multi-GB model family. **Never co-resident.** The
orchestrator pattern per stage: **load → run → POST `/free` (unload) → next**. Offload text encoders
(Mistral/Qwen2.5-VL/umt5) to system RAM where the node supports it. Peak VRAM spikes happen during
the *swap*, not steady state, so serialize hard.

---

## The rigging workaround (fully local, fully headless)

Meshy's single call = rig + skin + named animation baked into one GLB. Locally it's three headless
steps — no cloud, no GUI, no Mixamo/Adobe account:

### Humanoid characters
1. **Retopo first.** Hunyuan3D/TRELLIS output is dense triangle soup; skin weights go noisy on it.
   `blender --background --python scripts/retopo.py -- in.glb out.glb` (decimate ~24k tris, or
   Quad Remesher / Instant Meshes for clean quads).
2. **Rig** — choose by priority (verified trade-off):
   - **SkinTokens** (VAST-AI, MIT): best rig quality, handles **creatures**, `demo.py mesh.glb → rigged.glb`,
     ≥14 GB (run headless). **But its skeleton is learned/unnamed**, so step 3 must retarget by
     *position/hierarchy* (Rokoko, or a hand-built map after inspecting the output bones) — **`--direct` won't work.**
   - **MIA** (via ComfyUI-UniRig): outputs a **mixamorig** named skeleton → step 3 is trivial
     (`bake_anim.py --direct`). Downside: weights are **CC-BY-NC** (non-commercial).
   - **UniRig** (MIT) is the middle fallback.
   - Rule of thumb: **commercial / creatures → SkinTokens; easiest humanoid animation → MIA.**
3. **Bake a named clip** headlessly:
   `blender --background --python scripts/bake_anim.py -- --rig rigged.glb --clip anims/idle.fbx --name idle --out idle.glb`
   - If the clip is mixamorig-native (same bone names + T-pose): `--direct` = no retarget, just assign the Action.
   - Otherwise (CC0 clips below): the script maps bones, aligns rest pose via copy-rotation
     constraints, `nla.bake`s a clean named Action, and exports the GLB.

### Where the animation clips come from (OSS-redistributable)
| Source | License | Note |
|---|---|---|
| [RancidMilk free anims](https://rancidmilk.itch.io/free-character-animations) | CC0-ish (free, modify, redistribute) | 2,500+ CMU motions retargeted onto a CC0 rig, FBX — best bundle |
| [Mesh2Motion assets](https://github.com/Mesh2Motion/mesh2motion-assets) | CC0-1.0 | extractable `.blend`; own skeleton (needs BONE_MAP) |
| [CMU Mocap](https://mocap.cs.cmu.edu/) | public domain | BVH; most variety; needs retarget + cleanup |
| Mixamo | ❌ | clips are mixamorig-native but **cannot be redistributed** — do not bundle |

### Non-humanoid companions
- **SkinTokens** rigs creatures too — same tool as the characters, no separate rigger needed.
  (Fallbacks: UniRig, or RigAnything for template-free.)
- Animate via Mesh2Motion's **animal** skeletons + `bake_anim.py`, or hand-key in Blender.
- Still expect the most fixing here: missing tail/wing/ear bones, joint weight artifacts.

### Honest weak link
Rig + bake are both headless and scriptable. The fragile part is **rest-pose / bone-roll alignment**
during retarget: CC0 clips aren't mixamorig-native, so import them **without "Automatic Bone
Orientation"** and **validate the first character visually** before batching. Once a clip source is
dialed in, the rest of the roster is mechanical. Fine for a fixed roster; the per-character validation
makes a live CREATE-YOUR-OWN feature impractical (it assumed ~1-min cloud calls).

---

## Start here: one-character vertical slice
Before building all 8 stages, validate the two genuine unknowns end-to-end:
```
txt2img (Z-Image) -> Hunyuan3D 2.1 (2GP) -> retopo -> MIA rig -> bake one idle clip -> gltf-transform
```
If the sm_120 kernels compile and one rigged+animated GLB lands in Three.js looking right, the rest
of the stages are comparatively low-risk — the full pipeline reproduces locally.

> **Optional fallback (not required):** if you don't want to tune the rigging retarget at all, you can
> keep just the rig+animation stage on cloud Meshy and run everything else local. The goal here,
> though, is full local reproduction — and it works.

---

## Risks & ambiguities (read before committing time)

| Risk | Impact | Mitigation |
|---|---|---|
| **sm_120 kernel compile** (Hunyuan/3D-Pack) | Highest setup risk; ~a day | `TORCH_CUDA_ARCH_LIST=12.0`, build from source, older gcc via `CUDAHOSTCXX`. See `docs/01`. |
| **Rigging retarget alignment** | Rest-pose/bone-roll mismatch twists CC0 clips | Import clips w/o auto-bone-orientation; `bake_anim.py` BONE_MAP; validate char #1 visually |
| **Hunyuan3D paint > 16GB stock** | Texture pass OOMs | Use `Hunyuan3D-2GP` fork / `low_vram_mode` / lower `max_num_view` |
| **TRELLIS.2 needs 24GB** | Won't run cleanly on 16GB | Use Hunyuan3D 2.1; treat TRELLIS.2 as offload-only experiment |
| **No concurrency** | 10 chars ≈ 2–3 h serial | Queue overnight; this is the inherent single-GPU cost |
| **Licensing** if commercial | FLUX.2-9B 🔬, CHORD 🔬, RMBG-2.0 🔬, Hunyuan ⚠️ region | Swap to Z-Image-Turbo, QFX-PBR, BiRefNet, TRELLIS.2/Step1X (✅) |
| **Stack fragility** | Updates break torch/sm_120 | Pin torch; install xformers/flash-attn `--no-deps`; snapshot the working env |
| **mmproj / dual-model footguns** | Qwen edit & Wan fail silently | Qwen needs the `mmproj` file; Wan needs both high+low GGUFs, run sequentially |

## What stays identical to cloud
- `gltf-transform` compression (resize 1024 → webp q80 → draco) — same commands, byte-identical output.
- The Three.js scene, palette CSS-var system, floor/reflection/breathing logic, transition FX.
- The asset layout the front-end expects (`assets/floor/{charId}/`, portrait crops, etc.).
