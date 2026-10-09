"""Conservative syntax policy. This is defense in depth, NOT a Python sandbox."""

import ast
import hashlib

MAX_CODE_BYTES = 24000
MODULES = {"bpy", "math", "mathutils"}
BUILTINS = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "pow",
    "range",
    "reversed",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
}
FORBIDDEN_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "input",
    "print",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
    "dir",
    "type",
    "object",
    "super",
    "help",
    "breakpoint",
    "memoryview",
    "exit",
    "quit",
    "os",
    "sys",
    "subprocess",
    "socket",
    "ctypes",
    "pickle",
    "marshal",
    "importlib",
    "builtins",
    "requests",
    "urllib",
    "pathlib",
    "shutil",
    "io",
}
FORBIDDEN_ATTRS = {
    "app",
    "utils",
    "path",
    "types",
    "props",
    "msgbus",
    "wm",
    "script",
    "preferences",
    "window_manager",
    "windows",
    "screen",
    "screens",
    "workspace",
    "workspaces",
    "temp_override",
    "libraries",
    "images",
    "texts",
    "sounds",
    "movieclips",
    "cache_files",
    "volumes",
    "fonts",
    "load",
    "save",
    "write",
    "read",
    "filepath",
    "directory",
    "filename",
    "pack",
    "unpack",
    "driver_add",
    "driver_remove",
    "animation_data",
    "animation_data_create",
    "drivers",
    "handlers",
    "driver_namespace",
    "bl_rna",
    "rna_type",
    "id_data",
    "as_pointer",
    "path_resolve",
    "bl_idname",
    "register",
    "unregister",
    "user_remap",
    "library",
    "library_weak_reference",
    "exec",
    "execute",
    "invoke",
    "poll",
    "report",
    "render",
    "bake",
    "export_scene",
    "import_scene",
}
OPS = {
    "mesh.primitive_cube_add",
    "mesh.primitive_uv_sphere_add",
    "mesh.primitive_ico_sphere_add",
    "mesh.primitive_cylinder_add",
    "mesh.primitive_cone_add",
    "mesh.primitive_torus_add",
    "mesh.primitive_plane_add",
    "mesh.primitive_circle_add",
    "mesh.primitive_grid_add",
    "mesh.select_all",
    "mesh.remove_doubles",
    "mesh.merge_by_distance",
    "mesh.normals_make_consistent",
    "mesh.flip_normals",
    "mesh.extrude_region_move",
    "mesh.inset",
    "mesh.bevel",
    "mesh.subdivide",
    "object.select_all",
    "object.delete",
    "object.transform_apply",
    "object.modifier_apply",
    "object.join",
    "object.convert",
    "object.mode_set",
    "object.shade_smooth",
    "object.shade_flat",
    "transform.translate",
    "transform.rotate",
    "transform.resize",
    "curve.primitive_bezier_curve_add",
    "curve.primitive_bezier_circle_add",
}


class CodeRejected(ValueError):
    pass


def validate_code(code: str) -> str:
    if not isinstance(code, str) or not code.strip() or len(code.encode("utf-8")) > MAX_CODE_BYTES:
        raise CodeRejected("Código vazio ou maior que 24.000 bytes.")
    try:
        tree = ast.parse(code)
    except (SyntaxError, RecursionError, ValueError):
        raise CodeRejected("O código Blender contém sintaxe inválida.") from None
    nodes = list(ast.walk(tree))
    if len(nodes) > 6000:
        raise CodeRejected("O código Blender excede o limite de complexidade.")
    parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
    for node in nodes:
        if isinstance(
            node,
            (
                ast.ClassDef,
                ast.AsyncFunctionDef,
                ast.Await,
                ast.With,
                ast.AsyncWith,
                ast.Global,
                ast.Nonlocal,
                ast.Try,
                ast.Raise,
                ast.Delete,
            ),
        ):
            raise CodeRejected("Construção Python não permitida no worker.")
        if isinstance(node, (ast.FunctionDef, ast.arg)):
            name = node.name if isinstance(node, ast.FunctionDef) else node.arg
            if name.startswith("_") or name in FORBIDDEN_NAMES | MODULES:
                raise CodeRejected("Nome Python não permitido.")
        if isinstance(node, ast.Import):
            if any(alias.name not in MODULES or alias.asname for alias in node.names):
                raise CodeRejected("Importe somente bpy, math e mathutils, sem aliases.")
        if isinstance(node, ast.ImportFrom):
            if (
                node.level
                or node.module not in {"math", "mathutils"}
                or any(alias.name.startswith("_") or alias.name == "*" or alias.asname for alias in node.names)
            ):
                raise CodeRejected("Importação não permitida.")
        if isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in FORBIDDEN_NAMES:
                raise CodeRejected("Acesso a nomes privados, arquivos ou execução externa não permitido.")
            if isinstance(node.ctx, ast.Store) and node.id in MODULES | BUILTINS:
                raise CodeRejected("Não redefina módulos ou funções internas.")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in FORBIDDEN_ATTRS:
                raise CodeRejected("Acesso a atributo privado, arquivo ou operação externa não permitido.")
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "bpy"
                and node.attr not in {"ops", "data", "context"}
            ):
                raise CodeRejected("Somente bpy.ops, bpy.data e bpy.context são permitidos.")
            if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
                if (
                    node.value.value.id == "bpy"
                    and node.value.attr == "data"
                    and node.attr not in {"objects", "meshes", "materials", "curves", "collections"}
                ):
                    raise CodeRejected("Coleção bpy.data não permitida.")
            if isinstance(node.value, ast.Name) and node.value.id == "bpy" and node.attr == "ops":
                namespace = parents.get(node)
                operation = parents.get(namespace)
                call = parents.get(operation)
                if not (
                    isinstance(namespace, ast.Attribute)
                    and isinstance(operation, ast.Attribute)
                    and isinstance(call, ast.Call)
                    and call.func is operation
                    and f"{namespace.attr}.{operation.attr}" in OPS
                ):
                    raise CodeRejected("Operador Blender não permitido ou utilizado indiretamente.")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 4096:
            raise CodeRejected("Texto literal excede o limite permitido.")
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
