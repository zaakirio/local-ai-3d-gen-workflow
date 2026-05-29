# comfyui-workflows/

`orchestrate.py` loads one **API-format** workflow JSON per stage from this folder.

## Why these aren't pre-written
ComfyUI workflow graphs are large and tightly coupled to the **exact node versions** you install
(input keys, widget order, model filenames all differ per node release). Hand-authoring them blind
would produce files that silently fail to load. The reliable path is to build each graph once in the
ComfyUI UI from the node's own bundled example, then export it. That gives you a graph guaranteed to
match your installed nodes and downloaded filenames.

## How to produce each file
For every stage:
1. Launch ComfyUI (`python ~/ComfyUI/main.py`).
2. Start from the matching **bundled example** (below), or build the graph from the node's docs.
3. Point its loaders at the filenames you downloaded (see `docs/02-downloads.md`).
4. Generate once in the UI to confirm it works on 16GB.
5. **Export → "Save (API Format)"** and save here under the exact filename `orchestrate.py` expects.

> The UI "Save" and the **"Save (API Format)"** export are different files. `orchestrate.py` needs the
> **API format** (a flat `{node_id: {class_type, inputs}}` dict), not the UI graph.

## Files orchestrate.py expects
| File | Stage | Start from |
|---|---|---|
| `01_character_txt2img.json` | Character image + T-pose | Z-Image template, or FLUX.2 GGUF template + `comfyui_controlnet_aux` DWPose → ControlNet |
| `02_birefnet_cutout.json` | Background removal | `ComfyUI_BiRefNet_ll` example |
| `03_qwen_edit_companion.json` | Companion edit | Qwen-Image-Edit GGUF example (UnetLoaderGGUF + CLIPLoaderGGUF + mmproj) |
| `04_hunyuan3d_mesh.json` | Image → textured GLB | `ComfyUI-Hunyuan3DWrapper` example (enable low-VRAM/2GP) |
| `06_chord_pbr.json` | Floor PBR maps | `ComfyUI-Chord` example (or QFX-PBRGenerator for commercial) |
| `07_wan_i2v_loop.json` | Background video loop | Wan 2.2 I2V GGUF template (high→low noise, Lightning LoRA, first==last frame) |

Stages **05 retopo** and **rig+animation** are not ComfyUI graphs — they run via Blender headless /
ComfyUI-UniRig / Mesh2Motion (see `docs/03-pipeline.md`).

## Wiring orchestrate.py
After exporting, open each JSON, note the node ids for the prompt/seed/image inputs you want to vary
per character, and fill in `patch_inputs()` in `scripts/orchestrate.py` accordingly. Until then the
orchestrator runs each graph with its baked-in values.
