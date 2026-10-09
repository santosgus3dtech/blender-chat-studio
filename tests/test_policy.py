import pytest

from studio.policy import CodeRejected, validate_code


def test_accepts_real_modeling_operations():
    code = """import bpy
import math
from mathutils import Vector
bpy.ops.mesh.primitive_cube_add(size=20)
obj = bpy.context.object
obj.name = 'Cube'
obj.location = Vector((0, 0, 10))
bevel = obj.modifiers.new(name='Bevel', type='BEVEL')
bevel.width = 1
bpy.ops.object.modifier_apply(modifier=bevel.name)
"""
    assert len(validate_code(code)) == 64


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "import bpy as b",
        "from bpy import app",
        "from math import *",
        "open('/tmp/x','w')",
        "exec('1')",
        "getattr(bpy,'app')",
        "x = bpy.app",
        "x = bpy.context.preferences",
        "bpy.ops.wm.open_mainfile(filepath='/x')",
        "bpy.ops.script.python_file_run(filepath='/x')",
        "bpy.data.libraries.load('/x')",
        "bpy.ops.export_scene.gltf(filepath='/x')",
        "bpy.context.object.driver_add('location')",
        "x = (1).__class__",
        "x = bpy.ops; x.mesh.primitive_cube_add()",
        "bpy.ops.mesh.unknown()",
        "class X: pass",
        "try:\n pass\nexcept:\n pass",
        "def __evil(): pass",
        "bpy = 1",
        "x='" + "a" * 4097 + "'",
        "#" + "a" * 24001,
        "x = (",
        "",
    ],
)
def test_rejects_unsafe_or_unbounded_code(code):
    with pytest.raises(CodeRejected):
        validate_code(code)
