#!/usr/bin/env python3
"""
orchestrate.py — local replacement for the genmedia fan-out in fal-regenerate-3d.

Drives a running ComfyUI instance over its HTTP/WebSocket API, one stage at a time,
and UNLOADS each model before the next stage (a single 16GB card cannot hold two
stage models co-resident — this is the core constraint of the local port).

It loads an *API-format* workflow JSON per stage from ../comfyui-workflows/ (see that
folder's README for how to export those), patches a few inputs (prompt, seed, image
paths), queues it, waits for completion, then frees VRAM.

Usage:
    python orchestrate.py --char-id neon01 --prompt "cyberpunk operative, full body T-pose, ..."

This is a SKELETON: the node-id / input-key references in patch_inputs() depend on YOUR
exported workflow graphs. Wire them to the real ids once your workflows exist.
"""
import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
WF_DIR = Path(__file__).resolve().parent.parent / "comfyui-workflows"
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "output"

# Stage -> workflow file. Order matters; each runs then frees VRAM before the next.
STAGES = [
    ("character",  "01_character_txt2img.json"),
    ("cutout",     "02_birefnet_cutout.json"),
    ("companion",  "03_qwen_edit_companion.json"),
    ("mesh",       "04_hunyuan3d_mesh.json"),
    ("floor_pbr",  "06_chord_pbr.json"),
    ("bg_video",   "07_wan_i2v_loop.json"),
]
# Note: retopo (05) + rig/anim are handled by the Blender/UniRig steps in docs/03, not ComfyUI.


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{COMFY}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{COMFY}{path}") as r:
        return json.loads(r.read())


def free_vram():
    """Ask ComfyUI to unload models + free GPU memory between stages."""
    try:
        _post("/free", {"unload_models": True, "free_memory": True})
        time.sleep(2)
    except Exception as e:
        print(f"  (warning: /free failed: {e})")


def patch_inputs(graph: dict, ctx: dict) -> dict:
    """
    Patch per-run values into the API graph. Adjust the node ids/keys to match YOUR
    exported workflows. Example pattern:

        for nid, node in graph.items():
            ct = node.get("class_type", "")
            if ct in ("CLIPTextEncode",) and "positive" in node.get("_meta", {}).get("title", "").lower():
                node["inputs"]["text"] = ctx["prompt"]
            if ct == "KSampler":
                node["inputs"]["seed"] = ctx["seed"]
            if ct == "LoadImage" and "char" in node.get("_meta", {}).get("title", "").lower():
                node["inputs"]["image"] = ctx["character_image"]
    """
    return graph


def run_stage(name: str, wf_file: str, ctx: dict):
    path = WF_DIR / wf_file
    if not path.exists():
        print(f"[skip] {name}: {wf_file} not found — export it (see comfyui-workflows/README.md)")
        return
    print(f"[run ] {name} <- {wf_file}")
    graph = json.loads(path.read_text())
    graph = patch_inputs(graph, ctx)

    client_id = str(uuid.uuid4())
    resp = _post("/prompt", {"prompt": graph, "client_id": client_id})
    pid = resp.get("prompt_id")
    if not pid:
        print(f"  error queueing: {resp}")
        return

    # poll history until this prompt completes
    while True:
        time.sleep(2)
        hist = _get(f"/history/{pid}")
        if pid in hist and hist[pid].get("status", {}).get("completed", False):
            break
    print(f"  done: {name}")
    free_vram()   # <-- the critical 16GB step: unload before the next stage loads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char-id", required=True)
    ap.add_argument("--prompt", required=True, help="character txt2img prompt (force a T-pose)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = {
        "char_id": args.char_id,
        "prompt": args.prompt,
        "seed": args.seed,
        "character_image": f"{args.char_id}_character.png",
    }

    print(f"== local-ai-3d-gen :: character '{args.char_id}' ==")
    for name, wf in STAGES:
        run_stage(name, wf, ctx)

    print("\nComfyUI stages done. Remaining manual/CLI steps (see docs/03-pipeline.md):")
    print("  5. retopo   : blender --background --python scripts/retopo.py -- in.glb out.glb")
    print("  6. rig+anim : ComfyUI-UniRig (MIA) -> bake clip (Mesh2Motion / Blender / Mixamo) -> GLB")
    print("  9. compress : gltf-transform resize 1024 -> webp q80 -> draco")


if __name__ == "__main__":
    main()
