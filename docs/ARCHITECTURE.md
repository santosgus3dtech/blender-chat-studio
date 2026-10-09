# Architecture and Boundaries

The public extraction includes the worker protocol, AST policy, trusted Blender
wrapper and artifact validator. The MCP/CLI adapter is intentionally independent
of the operational application's store, accounts, gateway and inference provider.

## Execution

`execute_blender` validates a full scene script, then sends a bounded JSON-line
request over a Unix socket. The worker independently validates it and starts a
new background Blender process with factory settings and autoexec disabled.
The trusted wrapper exports all five artifacts. A missing/invalid artifact fails
the result before publication; each successful run receives a new UUID.

The client receives relative artifact paths, not an implemented HTTP download API.
No conversational persistence, model inference, public upload or web server exists
in this release. Follow-on work must not confuse these missing layers with the
functional execution core.

## Isolation

Worker: UID 10001, network disabled, root filesystem read-only, capabilities
dropped, no-new-privileges, bounded tmpfs, CPU, memory and process count. The only
persistent mount is the dedicated IPC volume. Generated code never receives the
tools container's output volume. There are no host bind mounts or Docker sockets.

The policy rejects non-modeling imports, filesystem/network/subprocess access,
private attributes, drivers, indirect operators and excessive code complexity.
This policy is not a security proof and is not a substitute for process/container
confinement. Blender and the container runtime remain part of the trusted base.

## Geometry and Fidelity

GLB export scales evaluated meshes from millimeters to meters; STL keeps mm.
Reports measure evaluated world-space dimensions and per-object edge topology.
They do not prove solid unions, detect all self-intersections, calculate loads,
select printing tolerances or validate a physical print. Multiple closed objects
can overlap and still require manual review or a separate CAD preparation step.

## Public/Private Separation

Only reviewed code files were extracted. Private deployment manifests, account
flows, model catalog responses, histories, logs, databases and real generated
artifacts were excluded. Public examples are newly authored reproducible scenes.
Future UI work must use a synthetic fixture contract and a read-only demo mode.
