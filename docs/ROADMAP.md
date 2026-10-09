# Public Portfolio Roadmap

## Delivered Foundation

Provider-free MCP/CLI core, restricted worker, artifact validation, original scene
examples, unit tests, CI and fresh repository history. Real Blender execution is
checked separately from syntax policy and MCP schema tests.

## Next: Interactive Showcase

Build a standalone React/TypeScript/Three.js workspace with a read-only chat replay,
visible revision history, GLB orbit/zoom/reset/wireframe, artifact downloads,
measurement reports and clear error/loading states. Match the existing private
workflow while keeping private branding, navigation and operations out of scope.

Acceptance: three original scenarios, a visible revision/comparison, no API call
or account required, honest recorded/deterministic labels, desktop/mobile canvas
pixel checks and browser QA. Do not present authored code as LLM-generated output.

## Then: Local Generation

Add a provider adapter only after the user's credential choice. Isolate credentials
from workers. Include explicit per-job limits, cancellation, immutable versions,
failed attempts, redacted errors and tests without provider access. Preserve the
offline showcase. Do not copy private OAuth clients, sessions or live histories.

## Later: Hosted Generation

Public read-only hosting and public arbitrary inference are different releases.
The latter requires authentication, per-user quotas, abuse controls, concurrency
limits, observability, artifact retention and a fresh security review. No current
issue or roadmap entry authorizes modifying the operational server.
