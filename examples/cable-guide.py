import bpy

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2))
base = bpy.context.object
base.name = "CableGuideBase"
base.dimensions = (45, 24, 4)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bevel = base.modifiers.new(name="BaseEdges", type="BEVEL")
bevel.width = 1
bevel.segments = 3
bpy.ops.object.modifier_apply(modifier=bevel.name)
for x in (-15, -5, 5, 15):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 7))
    tooth = bpy.context.object
    tooth.name = "CableDivider"
    tooth.dimensions = (3, 18, 10)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = tooth.modifiers.new(name="DividerEdges", type="BEVEL")
    bevel.width = 1
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
material = bpy.data.materials.new(name="Coral")
material.diffuse_color = (0.8, 0.2, 0.12, 1)
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.data.materials.append(material)
