# Security

Do not submit secrets, personal data or proprietary models in public issues.
For a suspected vulnerability, use GitHub private vulnerability reporting if it
is enabled; otherwise contact the maintainer without posting exploit details.

This is a portfolio foundation, not a hardened multi-tenant execution service.
Do not expose the worker or MCP execution tool to anonymous internet users.
Do not replace the worker with host Python/Blender execution.

Containers must remain non-root, read-only, resource-limited and networkless,
without credentials, host bind mounts or the Docker socket. Policy validation is
defense in depth and cannot guarantee isolation by itself.

Output headers and geometry reports are bounded sanity checks, not a complete
malware parser or manufacturing certification. Open downloaded BLEND files only
from trusted sources and keep automatic script execution disabled.
