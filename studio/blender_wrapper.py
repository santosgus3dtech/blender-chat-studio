"""Trusted Blender entry point. Never loaded into the application interpreter."""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

# Blender ignores PYTHONPATH unless system-env is enabled. Trust only our own path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.policy import BUILTINS, validate_code


def generate(code: str, output: Path, preview_size: int) -> dict:
    validate_code(code)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    import builtins
    import mathutils

    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name not in {"bpy", "math", "mathutils"} or level:
            raise ImportError("Importação não permitida.")
        return {"bpy": bpy, "math": math, "mathutils": mathutils}[name]

    safe_builtins = {name: getattr(builtins, name) for name in BUILTINS}
    safe_builtins["__import__"] = safe_import
    namespace = {"__builtins__": safe_builtins, "bpy": bpy, "math": math, "mathutils": mathutils}
    exec(compile(code, "<generated-blender>", "exec"), namespace, namespace)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    meshes = [obj for obj in scene.objects if obj.type in {"MESH", "CURVE", "SURFACE", "FONT"}]
    if not meshes:
        raise ValueError("empty_scene")
    # Evaluate modifiers and transforms for dimensions and topology reporting.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points, vertices, triangles, watertight = [], 0, 0, True
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        mesh.calc_loop_triangles()
        vertices += len(mesh.vertices)
        triangles += len(mesh.loop_triangles)
        if vertices > 500000 or triangles > 1000000:
            raise ValueError("geometry_limit")
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        edge_faces = {tuple(sorted(edge.vertices)): 0 for edge in mesh.edges}
        for polygon in mesh.polygons:
            for edge in polygon.edge_keys:
                key = tuple(sorted(edge))
                edge_faces[key] = edge_faces.get(key, 0) + 1
        watertight = watertight and bool(edge_faces) and all(count == 2 for count in edge_faces.values())
        evaluated.to_mesh_clear()
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise ValueError("invalid_geometry")
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    extent = high - low
    if max(extent) <= 0 or max(extent) > 100000:
        raise ValueError("invalid_dimensions")
    warnings = [] if watertight else ["A malha possui bordas abertas ou não manifold; revise antes de imprimir."]
    if len(meshes) > 1:
        warnings.append("Os objetos não foram certificados como uma união sólida sem interseções.")
    report = {
        "blender_version": bpy.app.version_string,
        "units": "mm",
        "dimensions_mm": dict(zip(("x", "y", "z"), (round(float(value), 5) for value in extent))),
        "objects": len(meshes),
        "vertices": vertices,
        "triangles": triangles,
        "watertight": watertight,
        "warnings": warnings,
    }
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = []
    for obj in meshes:
        # glTF ignores scene display units. Export detached evaluated copies in meters.
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
        copy = bpy.data.objects.new(obj.name + "_export", mesh)
        scene.collection.objects.link(copy)
        copy.matrix_world = Matrix.Scale(0.001, 4) @ obj.matrix_world
        copy.select_set(True)
        export_objects.append((copy, obj.matrix_world.copy()))
    bpy.context.view_layer.objects.active = export_objects[0][0]
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(output / "model.glb"), export_format="GLB", use_selection=True)
    for copy, matrix in export_objects:
        copy.matrix_world = matrix
    bpy.context.view_layer.update()
    # Blender 3.4 uses the STL add-on; 4+ provides the native wm exporter.
    if bpy.app.version >= (4, 0, 0):
        bpy.ops.wm.stl_export(
            filepath=str(output / "model.stl"),
            export_selected_objects=True,
            apply_modifiers=True,
            global_scale=1.0,
            use_scene_unit=False,
        )
    else:
        bpy.ops.export_mesh.stl(
            filepath=str(output / "model.stl"),
            use_selection=True,
            use_mesh_modifiers=True,
            global_scale=1.0,
            use_scene_unit=False,
        )
    for copy, _ in export_objects:
        mesh = copy.data
        bpy.data.objects.remove(copy, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    center = (low + high) / 2
    radius = max(extent.length / 2, 0.01)
    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((1.3, -1.7, 1.2)).normalized() * radius * 3.8
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = radius * 2.5
    camera_data.clip_start = max(radius / 1000, 0.001)
    camera_data.clip_end = radius * 100
    scene.camera = camera
    for index, direction in enumerate(((1, -2, 3), (-2, -1, 1), (1, 2, 2))):
        light_data = bpy.data.lights.new("PreviewLight" + str(index), "AREA")
        light_data.energy = radius * radius * (80 if index == 0 else 35)
        light_data.shape = "DISK"
        light_data.size = radius * 3
        light = bpy.data.objects.new(light_data.name, light_data)
        scene.collection.objects.link(light)
        light.location = center + Vector(direction) * radius * 2
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.18, 0.22, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = preview_size
    scene.render.resolution_y = preview_size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output / "preview.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "scene.blend"), check_existing=False)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=True, allow_nan=False), encoding="utf-8")
    return report


def main():
    args = sys.argv[sys.argv.index("--") + 1 :]
    root = Path(args[0]).resolve()
    try:
        request = json.loads((root / "request.json").read_text(encoding="utf-8"))
        generate(request["code"], root, int(request["preview_size"]))
    except BaseException as error:
        # No generated-code/provider content in logs returned to the application.
        (root / "failure.json").write_text(json.dumps({"type": type(error).__name__}), encoding="utf-8")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
