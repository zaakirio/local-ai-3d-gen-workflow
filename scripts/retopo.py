"""
retopo.py — headless Blender decimation for Hunyuan3D/TRELLIS output before rigging.

Dense triangle-soup meshes give noisy skin weights; this decimates to a rig-friendly
budget. For production-clean quads use Quad Remesher / Instant Meshes instead.

Usage:
    blender --background --python scripts/retopo.py -- input.glb output.glb [target_tris]
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
target_tris = int(argv[2]) if len(argv) > 2 else 24000

# clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for obj in meshes:
    bpy.context.view_layer.objects.active = obj
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris > target_tris:
        m = obj.modifiers.new("decimate", "DECIMATE")
        m.ratio = max(0.02, target_tris / tris)
        bpy.ops.object.modifier_apply(modifier=m.name)
    # recompute normals so downstream PBR/lighting is correct
    obj.data.use_auto_smooth = True

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format="GLB",
    export_apply=True,
    export_yup=True,
)
print(f"[retopo] {src} -> {dst}  (target ~{target_tris} tris)")
