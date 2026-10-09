# Blender Chat Studio - Public Portfolio

Work only in this public repository. Read README.md, docs/ARCHITECTURE.md and
docs/ROADMAP.md before editing. Keep the private operational edition untouched.

- Never copy a private Git history, runtime database, conversation, account session,
  credential, local deployment configuration, infrastructure address or customer model.
- `.env.local` may exist locally. Never read its value into logs or stage it.
- Use original synthetic models or assets with a verified redistributable license.
- Label deterministic examples, chat replays and real AI generations distinctly.
- Do not claim that topology checks certify printable or mechanically safe parts.
- Never execute generated code on the host. Preserve the isolated Linux worker:
  no network, host directories, credentials, Docker socket or privileged capabilities.
- Do not turn the MCP tools into an anonymous public execution endpoint.
- This first release has no provider. Obtain a separate credential decision before
  implementing provider-backed generation; do not silently reuse local secrets.
- Run `uv run --locked ruff check studio tests examples` and `uv run --locked pytest -q`.
- Keep provider-free CI usable; real Blender tests require isolated Linux containers.
- Do not publish or change production services without an explicit deployment request.
