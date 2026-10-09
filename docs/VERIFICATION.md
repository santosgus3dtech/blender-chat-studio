# Foundation Verification - 2026-10-08

## Local checks

- 42 provider-free unit tests passed on Windows/Python 3.14.
- Ruff passed for source, tests and example scripts.
- Both Linux container images built; tools dependencies were locked and hash-checked.
- Actual Blender 3.4.1 exported all five required artifacts for each original scene.
- Three PNG previews were visually inspected and contain the expected geometry.
- Worker inspection confirmed UID 10001, no network, read-only root, dropped
  capabilities, no-new-privileges and only the dedicated IPC named-volume mount.

| Example | World dimensions, mm | Objects | Triangles | Per-object closed topology |
| --- | --- | --- | --- | --- |
| Beveled cube | 20 x 20 x 20 | 1 | 188 | true |
| Cable guide | 45 x 24 x 12 | 5 | 940 | true |
| Desk organizer | 70 x 50 x 30 | 6 | 72 | true |

The multi-object scenes are **not certified solid unions**. The reports retain
that warning. No physical print, tolerance, strength, slicing or AI generation
was tested or claimed by these authored examples.

Public artifacts include only the original GLB/STL/PNG/report exports. The worker
also generates BLEND files, but they are not included in the checked-in fixtures.
Generated runtime files remain in a separate local named volume, not Git.

The MCP smoke command independently checks stdio tool discovery, worker health,
a real 20 mm cube and a GLB extent of 0.020 m. It contains no provider code and
does not require a credential. Run it only with the restricted worker available.
