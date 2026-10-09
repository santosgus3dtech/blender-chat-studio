import bpy

bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, 10))
cube = bpy.context.object
cube.name = "BeveledCalibrationCube"
bevel = cube.modifiers.new(name="RoundedEdges", type="BEVEL")
bevel.width = 1
bevel.segments = 3
bpy.ops.object.modifier_apply(modifier=bevel.name)
material = bpy.data.materials.new(name="Teal")
material.diffuse_color = (0.02, 0.55, 0.45, 1)
cube.data.materials.append(material)
