"""
bake_anim.py — headless Blender: bind a named animation clip onto an MIA-rigged GLB
and export a GLB with the baked clip. Closes the local rigging+animation gap (no cloud,
no Mixamo/Adobe account).

RIGGER NOTE (verified): MIA outputs a MIXAMORIG (named) skeleton -> --direct works if the clip is
also mixamorig. SkinTokens / UniRig output a PREDICTED / unnamed skeleton -> --direct will NOT work;
you must retarget by position (Rokoko, or fill BONE_MAP after inspecting the actual predicted bone
names in the rigged GLB). Inspect with: print([b.name for b in armature.pose.bones]).

Two modes:
  --direct      clip AND rig share the same (mixamorig) bone names + T-pose rest pose. MIA-rig only.
  (default)     retarget: maps clip bones -> rig bones via BONE_MAP, aligns rest pose with
                copy-rotation constraints, then nla.bake into a clean named Action. Use for CC0
                clips (CMU / Mesh2Motion / RancidMilk) and for SkinTokens/UniRig rigs.

Usage:
  blender --background --python scripts/bake_anim.py -- \
      --rig character_rigged.glb --clip assets/anims/idle.fbx --name idle --out idle.glb [--direct]

NOTE: rest-pose + bone-roll alignment is the fragile part. Import clips WITHOUT
"Automatic Bone Orientation" so rolls stay raw and match MIA's mixamorig output.
Validate the first character visually before batching.
"""
import sys
import bpy

# clip-skeleton bone name -> mixamorig bone name. Fill for your CC0 clip source.
# CMU/Mesh2Motion rigs differ; this is the retarget contract. Empty entries are skipped.
BONE_MAP = {
    "Hips": "mixamorig:Hips",
    "Spine": "mixamorig:Spine",
    "Spine1": "mixamorig:Spine1",
    "Spine2": "mixamorig:Spine2",
    "Neck": "mixamorig:Neck",
    "Head": "mixamorig:Head",
    "LeftArm": "mixamorig:LeftArm",
    "LeftForeArm": "mixamorig:LeftForeArm",
    "LeftHand": "mixamorig:LeftHand",
    "RightArm": "mixamorig:RightArm",
    "RightForeArm": "mixamorig:RightForeArm",
    "RightHand": "mixamorig:RightHand",
    "LeftUpLeg": "mixamorig:LeftUpLeg",
    "LeftLeg": "mixamorig:LeftLeg",
    "LeftFoot": "mixamorig:LeftFoot",
    "RightUpLeg": "mixamorig:RightUpLeg",
    "RightLeg": "mixamorig:RightLeg",
    "RightFoot": "mixamorig:RightFoot",
}


def parse_args():
    a = sys.argv[sys.argv.index("--") + 1:]
    d = {"direct": "--direct" in a}
    for k in ("rig", "clip", "name", "out"):
        d[k] = a[a.index(f"--{k}") + 1]
    return d


def import_clip(path):
    if path.lower().endswith(".glb") or path.lower().endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:  # FBX clip (cm units, keep raw bone orientation so rolls match mixamorig)
        bpy.ops.import_scene.fbx(filepath=path, global_scale=0.01,
                                 use_manual_orientation=False, automatic_bone_orientation=False)
    arms = [o for o in bpy.context.selected_objects if o.type == "ARMATURE"]
    return arms[0]


def find_target():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    return arms[0] if arms else None


def main():
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.import_scene.gltf(filepath=args["rig"])
    tgt = find_target()
    if tgt is None:
        raise SystemExit("no armature found in rig GLB")

    src = import_clip(args["clip"])
    action = src.animation_data.action

    if args["direct"]:
        # bone names + rest pose already match -> just assign the Action
        if tgt.animation_data is None:
            tgt.animation_data_create()
        tgt.animation_data.action = action
        action.name = args["name"]
    else:
        # retarget: constrain target bones to source bones, bake, drop constraints
        scene = bpy.context.scene
        scene.frame_start = int(action.frame_range[0])
        scene.frame_end = int(action.frame_range[1])
        src.animation_data.action = action

        bpy.context.view_layer.objects.active = tgt
        bpy.ops.object.mode_set(mode="POSE")
        for src_name, tgt_name in BONE_MAP.items():
            pb = tgt.pose.bones.get(tgt_name)
            if not pb or src_name not in src.pose.bones:
                continue
            c = pb.constraints.new("COPY_ROTATION")
            c.target = src
            c.subtarget = src_name
            if tgt_name.endswith("Hips"):  # root also follows translation
                t = pb.constraints.new("COPY_LOCATION")
                t.target = src
                t.subtarget = src_name
        # bake the constrained motion into a clean Action, then clear constraints
        bpy.ops.nla.bake(frame_start=scene.frame_start, frame_end=scene.frame_end,
                         only_selected=False, visual_keying=True, clear_constraints=True,
                         bake_types={"POSE"})
        bpy.ops.object.mode_set(mode="OBJECT")
        tgt.animation_data.action.name = args["name"]
        bpy.data.objects.remove(src, do_unlink=True)

    bpy.ops.export_scene.gltf(filepath=args["out"], export_format="GLB",
                              export_animations=True, export_animation_mode="ACTIONS")
    print(f"[bake_anim] {args['rig']} + {args['clip']} -> {args['out']} (clip '{args['name']}')")


if __name__ == "__main__":
    main()
