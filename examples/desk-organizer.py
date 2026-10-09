import bpy

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2))
base = bpy.context.object
base.name = "OrganizerFloor"
base.dimensions = (70, 50, 4)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
walls = ((0, -23, 70, 4), (0, 23, 70, 4), (-33, 0, 4, 42), (33, 0, 4, 42), (0, 0, 4, 42))
for x, y, width, depth in walls:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 15))
    wall = bpy.context.object
    wall.name = "OrganizerWall"
    wall.dimensions = (width, depth, 30)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
material = bpy.data.materials.new(name="Green")
material.diffuse_color = (0.15, 0.45, 0.25, 1)
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.data.materials.append(material)
