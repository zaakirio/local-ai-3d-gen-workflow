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

## The rigging workaround (the only real gap)

Meshy's single call = rig + skin + named animation baked into one GLB. Locally, split it:

### Humanoid characters (best path)
1. **Retopo first.** Hunyuan3D/TRELLIS output is dense triangle soup; skin weights go noisy on it.
   Headless Blender: `blender --background --python scripts/retopo.py -- in.glb out.glb`
   (decimate to ~15–30k tris, or Quad Remesher / Instant Meshes for clean quads).
2. **MIA (Make-It-Animatable)** via ComfyUI-UniRig → predicts blend weights + a **standard 65-bone
   mixamorig skeleton** in ~1s. Because it's Mixamo-compatible, any Mixamo clip retargets onto it.
3. **Bake a named clip**, two options:
   - *Fully local:* apply a CC0 clip in **Mesh2Motion** (GUI: fit skeleton, pick idle/dance/alert,
     export multi-clip GLB), or a Blender headless script that loads a mixamorig `.fbx` clip and
     exports glTF with `export_animations=True`.
   - *Browser:* upload to **Mixamo**, pick clips, download FBX, then `FBX2glTF --binary --anim-framerate bake30`.

### Non-humanoid companions (harder)
- **UniRig** (bundled, MIT) or **RigAnything** — both template-free, handle creatures. Rigging only.
- Animate via Mesh2Motion's **animal** skeletons, or hand-key in Blender.
- Expect the most manual fixing here: missing tail/wing/ear bones, joint weight artifacts.

### Honest gap summary
- Rigging itself = automatable + headless. **Animation baking is the weak link** — every route has
  a GUI step or a hand-written Blender export script. There is no turnkey "mesh in → multi-clip GLB out".
- Budget **a manual cleanup pass per character**. Fine for a fixed roster; painful for a live
  CREATE-YOUR-OWN feature (which assumed ~1-min cloud calls).

---

## Start here: one-character vertical slice
Before building all 8 stages, validate the two genuine unknowns end-to-end:
```
txt2img (Z-Image) -> Hunyuan3D 2.1 (2GP) -> retopo -> MIA rig -> bake one idle clip -> gltf-transform
```
If the sm_120 kernels compile and one rigged+animated GLB lands in Three.js looking right, the rest
of the stages are comparatively low-risk. If rigging quality disappoints, that's your signal to keep
**cloud Meshy for stage 6 only** and run everything else local (the recommended hybrid).

---

## Risks & ambiguities (read before committing time)

| Risk | Impact | Mitigation |
|---|---|---|
| **sm_120 kernel compile** (Hunyuan/3D-Pack) | Highest setup risk; ~a day | `TORCH_CUDA_ARCH_LIST=12.0`, build from source, older gcc via `CUDAHOSTCXX`. See `docs/01`. |
| **Rigging not 1:1 with Meshy** | Manual pass per character; no named-clip library | MIA→Mixamo for humanoids; consider hybrid (cloud Meshy) at volume |
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
